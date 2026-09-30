# file: openhands/server/session/agent_session.py:304-392
# asked: {"lines": [324, 325, 327, 328, 330, 331, 332, 335, 336, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354, 355, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 373, 374, 375, 376, 377, 378, 379, 381, 383, 384, 386, 387, 389, 390, 392], "branches": [[324, 325], [324, 327], [332, 335], [332, 353], [377, 378], [377, 381]]}
# gained: {"lines": [324, 327, 328, 330, 331, 332, 335, 336, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 373, 374, 375, 376, 377, 378, 379, 381, 383, 384, 386, 387, 389, 390, 392], "branches": [[324, 327], [332, 335], [332, 353], [377, 378]]}

import asyncio
import importlib
import types

import pytest


@pytest.mark.asyncio
async def test_create_runtime_remote_success(monkeypatch):
    # Import the module under test
    mod = importlib.import_module("openhands.server.session.agent_session")
    AgentSession = mod.AgentSession

    # Fake Secrets handler used by the module
    class FakeSecrets:
        def __init__(self, custom_secrets=None):
            self.custom_secrets = custom_secrets or {}

        def get_env_vars(self):
            # Return env vars based on provided custom_secrets for verification
            return {"CUSTOM_A": "valA", **{f"CUST_{k.upper()}": v for k, v in (self.custom_secrets or {}).items()}}

    monkeypatch.setattr(mod, "Secrets", FakeSecrets)

    # Create a fake RemoteRuntime class. We'll patch both get_runtime_cls to return it
    # and RemoteRuntime symbol to this class so the equality check matches.
    created_args = {}

    class FakeRemoteRuntime:
        def __init__(self, *args, **kwargs):
            # store args for assertions
            created_args["init_args"] = args
            created_args["init_kwargs"] = kwargs
            # ensure plugins is set (session logs plugins later)
            self.plugins = kwargs.get("plugins", [])

        async def connect(self):
            # Successful connect
            created_args["connected"] = True

        async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
            created_args["clone_called_with"] = (git_provider_tokens, selected_repository, selected_branch)

        # these are sync functions that will be run via call_sync_from_async
        def maybe_run_setup_script(self):
            created_args["ran_setup"] = True

        def maybe_setup_git_hooks(self):
            created_args["ran_hooks"] = True

    # Patch get_runtime_cls to return our FakeRemoteRuntime and RemoteRuntime symbol to same class
    monkeypatch.setattr(mod, "get_runtime_cls", lambda name: FakeRemoteRuntime)
    monkeypatch.setattr(mod, "RemoteRuntime", FakeRemoteRuntime)

    # Prepare a fake agent with sandbox_plugins
    class Plugin:
        def __init__(self, name):
            self.name = name

    fake_agent = types.SimpleNamespace(sandbox_plugins=[Plugin("p1"), Plugin("p2")])

    # Create an AgentSession instance
    # Provide minimal stubs for file_store, llm_registry, conversation_stats
    session = AgentSession(
        sid="s123",
        file_store=object(),
        llm_registry=object(),
        conversation_stats=object(),
        status_callback=None,
        user_id="u1",
    )

    # Patch override_provider_tokens_with_custom_secret to ensure it's called and returns overridden tokens
    override_called = {}

    def fake_override(git_provider_tokens, custom_secrets):
        override_called["args"] = (git_provider_tokens, custom_secrets)
        return {"overridden": "tok"}

    monkeypatch.setattr(session, "override_provider_tokens_with_custom_secret", fake_override)

    # Run the _create_runtime async method
    res = await session._create_runtime(
        runtime_name="remote-runtime",
        config=object(),
        agent=fake_agent,
        git_provider_tokens={"git": "token"},
        custom_secrets={"a": "b"},
        selected_repository="repo",
        selected_branch="main",
    )

    # Assertions
    assert res is True
    assert isinstance(session.runtime, FakeRemoteRuntime)
    # override_provider_tokens_with_custom_secret should have been called with provided tokens and custom_secrets
    assert override_called["args"] == ({"git": "token"}, {"a": "b"})
    # connect flag set
    assert created_args.get("connected", False) is True
    # clone_or_init_repo called with original git_provider_tokens and repository info
    assert created_args.get("clone_called_with") == ({"git": "token"}, "repo", "main")
    # The call_sync_from_async should have caused the sync methods to run
    assert created_args.get("ran_setup", False) is True
    assert created_args.get("ran_hooks", False) is True
    # Ensure env_vars included custom secret transformed by FakeSecrets
    assert "CUSTOM_A" in created_args["init_kwargs"].get("env_vars", {})


@pytest.mark.asyncio
async def test_create_runtime_non_remote_connect_failure_and_status_callback(monkeypatch):
    mod = importlib.import_module("openhands.server.session.agent_session")
    AgentSession = mod.AgentSession

    # Fake Secrets handler
    class FakeSecrets:
        def __init__(self, custom_secrets=None):
            self.custom_secrets = custom_secrets or {}

        def get_env_vars(self):
            return {"CUST": "v"}

    monkeypatch.setattr(mod, "Secrets", FakeSecrets)

    # Define a sentinel RemoteRuntime different from the runtime we will return
    class SentinelRemote:
        pass

    monkeypatch.setattr(mod, "RemoteRuntime", SentinelRemote)

    # Fake provider handler used when runtime is not RemoteRuntime
    class FakeProviderHandler:
        def __init__(self, provider_tokens=None):
            self.provider_tokens = provider_tokens

        async def get_env_vars(self, expose_secrets=False):
            # Return some env vars that will be merged
            return {"PROV": "pv"}

    monkeypatch.setattr(mod, "ProviderHandler", FakeProviderHandler)

    # We'll need to ensure the function get_runtime_cls returns a class different from RemoteRuntime.
    class FakeOtherRuntime:
        def __init__(self, *args, **kwargs):
            self.plugins = kwargs.get("plugins", [])

        async def connect(self):
            # Simulate connection failure by raising the specific exception type used in module
            raise mod.AgentRuntimeUnavailableError("cannot connect")

        async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
            # should not be called in this failure scenario
            raise AssertionError("clone_or_init_repo should not be called on failed connect")

        def maybe_run_setup_script(self):
            raise AssertionError("setup script should not be called on failed connect")

        def maybe_setup_git_hooks(self):
            raise AssertionError("git hooks should not be called on failed connect")

    monkeypatch.setattr(mod, "get_runtime_cls", lambda name: FakeOtherRuntime)

    # Patch RuntimeStatus to have the ERROR_RUNTIME_DISCONNECTED attribute expected
    class FakeRuntimeStatus:
        ERROR_RUNTIME_DISCONNECTED = "ERR_RUNTIME_DISCONNECTED"

    monkeypatch.setattr(mod, "RuntimeStatus", FakeRuntimeStatus)

    # Patch AgentRuntimeUnavailableError in module to the existing one or a new one if not present.
    # We will raise the same type from FakeOtherRuntime.connect; the module already references AgentRuntimeUnavailableError,
    # but ensure it's present and is a class we can use.
    if not hasattr(mod, "AgentRuntimeUnavailableError"):
        class ARUError(Exception):
            pass
        monkeypatch.setattr(mod, "AgentRuntimeUnavailableError", ARUError)

    # Prepare a fake agent with no plugins
    fake_agent = types.SimpleNamespace(sandbox_plugins=[])

    # Capture status_callback calls
    status_calls = []

    def status_callback(level, status_code, message):
        status_calls.append((level, status_code, message))

    # Create session instance
    session = AgentSession(
        sid="s_fail",
        file_store=object(),
        llm_registry=object(),
        conversation_stats=object(),
        status_callback=status_callback,
        user_id=None,
    )

    # Call _create_runtime which should attempt connect and hit exception, returning False and calling status_callback
    res = await session._create_runtime(
        runtime_name="non-remote",
        config=object(),
        agent=fake_agent,
        git_provider_tokens={"gitprov": "t"},
        custom_secrets=None,
        selected_repository=None,
        selected_branch=None,
    )

    assert res is False
    # status_callback should have been called exactly once with 'error', ERROR_RUNTIME_DISCONNECTED, and the exception message
    assert len(status_calls) == 1
    level, status_code, message = status_calls[0]
    assert level == "error"
    assert status_code == FakeRuntimeStatus.ERROR_RUNTIME_DISCONNECTED
    assert "cannot connect" in message
