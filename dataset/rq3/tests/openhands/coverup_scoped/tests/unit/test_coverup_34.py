# file: openhands/runtime/impl/local/local_runtime.py:145-217
# asked: {"lines": [159, 160, 161, 162, 166, 167, 169, 170, 175, 176, 180, 181, 182, 183, 185, 186, 188, 189, 190, 191, 194, 195, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 213, 214, 215, 216, 217], "branches": [[160, 161], [160, 166], [194, 195], [194, 198], [215, 0], [215, 216]]}
# gained: {"lines": [159, 160, 161, 162, 166, 167, 169, 170, 175, 176, 180, 181, 182, 183, 185, 186, 188, 189, 190, 191, 194, 195, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 213, 214, 215, 216, 217], "branches": [[160, 161], [160, 166], [194, 195], [194, 198], [215, 0], [215, 216]]}

import sys
import types
import importlib
import os
import pytest

def _make_fake_parent_init():
    def fake_init(self, config, event_stream, llm_registry, sid, plugins, env_vars, status_callback, attach_to_existing, headless_mode, user_id, git_provider_tokens):
        # Minimal attributes that LocalRuntime expects after super().__init__
        self.session = types.SimpleNamespace(headers={})
    return fake_init

def _make_fake_logger():
    class FakeLogger:
        def __init__(self):
            self.warnings = []

        def warning(self, msg):
            self.warnings.append(msg)

        def debug(self, msg):
            pass
    return FakeLogger()

@pytest.fixture(autouse=True)
def ensure_clean_env(monkeypatch):
    # Ensure SESSION_API_KEY and TEST_VAR not leaking between tests unless explicitly set
    monkeypatch.delenv('SESSION_API_KEY', raising=False)
    monkeypatch.delenv('TEST_VAR', raising=False)
    yield
    # Cleanup after test
    monkeypatch.delenv('SESSION_API_KEY', raising=False)
    monkeypatch.delenv('TEST_VAR', raising=False)

def test_local_runtime_windows_with_env_and_session_key(monkeypatch):
    # Import module under test
    module_path = "openhands.runtime.impl.local.local_runtime"
    local_runtime = importlib.import_module(module_path)
    importlib.reload(local_runtime)

    # Patch ActionExecutionClient.__init__ to a no-op that sets a session with headers
    fake_init = _make_fake_parent_init()
    monkeypatch.setattr(local_runtime.ActionExecutionClient, "__init__", fake_init, raising=True)

    # Patch get_user_info to return deterministic values
    monkeypatch.setattr(local_runtime, "get_user_info", lambda: ("uid-123", "user-abc"), raising=True)

    # Force platform to windows to hit the is_windows branch and capture logger warnings
    monkeypatch.setattr(sys, "platform", "win32")
    fake_logger = _make_fake_logger()
    monkeypatch.setattr(local_runtime, "logger", fake_logger, raising=True)

    # Create a fake config with sandbox settings including runtime_startup_env_vars
    sandbox = types.SimpleNamespace(local_runtime_url="http://localhost", runtime_startup_env_vars={"TEST_VAR": "VALUE1"})
    fake_config = types.SimpleNamespace(sandbox=sandbox)

    # Ensure SESSION_API_KEY is set so the branch at lines 213-217 runs
    monkeypatch.setenv("SESSION_API_KEY", "supersecret")

    # Create minimal placeholders for required args
    fake_event_stream = object()
    fake_llm_registry = object()

    # Instantiate LocalRuntime - this should execute the branches in question
    runtime = local_runtime.LocalRuntime(fake_config, fake_event_stream, fake_llm_registry)

    # Assertions to verify postconditions
    assert runtime.is_windows is True
    # get_user_info values applied
    assert runtime._user_id == "uid-123"
    assert runtime._username == "user-abc"
    # env var from config.sandbox.runtime_startup_env_vars should be in os.environ
    assert os.environ.get("TEST_VAR") == "VALUE1"
    # api_url built with default -1 port
    assert runtime.api_url == "http://localhost:-1"
    # session header should be set from SESSION_API_KEY
    assert getattr(runtime, "_session_api_key") == "supersecret"
    assert runtime.session.headers.get("X-Session-API-Key") == "supersecret"
    # logger.warning should have been called at least once (windows and initialization warnings)
    assert any("Running on Windows" in w for w in fake_logger.warnings)
    assert any("Initializing LocalRuntime" in w for w in fake_logger.warnings)

def test_local_runtime_non_windows_no_session_key(monkeypatch):
    # Import module under test
    module_path = "openhands.runtime.impl.local.local_runtime"
    local_runtime = importlib.import_module(module_path)
    importlib.reload(local_runtime)

    # Patch ActionExecutionClient.__init__ as before
    fake_init = _make_fake_parent_init()
    monkeypatch.setattr(local_runtime.ActionExecutionClient, "__init__", fake_init, raising=True)

    # Patch get_user_info to different deterministic values
    monkeypatch.setattr(local_runtime, "get_user_info", lambda: ("uid-999", "user-xyz"), raising=True)

    # Force platform to linux to take the non-windows branch
    monkeypatch.setattr(sys, "platform", "linux")

    # Use config with no runtime_startup_env_vars (falsy) to avoid updating os.environ
    sandbox = types.SimpleNamespace(local_runtime_url="http://127.0.0.1", runtime_startup_env_vars=None)
    fake_config = types.SimpleNamespace(sandbox=sandbox)

    # Ensure SESSION_API_KEY and TEST_VAR are not set
    monkeypatch.delenv("SESSION_API_KEY", raising=False)
    monkeypatch.delenv("TEST_VAR", raising=False)

    fake_event_stream = object()
    fake_llm_registry = object()

    runtime = local_runtime.LocalRuntime(fake_config, fake_event_stream, fake_llm_registry)

    # Assertions
    assert runtime.is_windows is False
    assert runtime._user_id == "uid-999"
    assert runtime._username == "user-xyz"
    # Since runtime_startup_env_vars was None, TEST_VAR should not be set by this config
    assert os.environ.get("TEST_VAR") is None
    # No session api key should have been set
    assert runtime._session_api_key is None
    assert "X-Session-API-Key" not in runtime.session.headers
    # api_url should reflect provided local_runtime_url and default -1 port
    assert runtime.api_url == "http://127.0.0.1:-1"
