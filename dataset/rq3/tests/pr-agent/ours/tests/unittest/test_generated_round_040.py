import os
import tempfile

import pytest

from pr_agent.git_providers import utils
from pr_agent.git_providers.utils import apply_repo_settings


def test_apply_repo_settings_sets_model_round_040(monkeypatch):
    """
    Verify that when repo settings loading is disabled, the model-checking branch calls set_claude_model
    and the AUTO_CAST_FOR_DYNACONF environment variable is set to "false" deterministically.
    """
    called = {"set_claude": False}

    class FakeSettingsNoRepo:
        def __init__(self):
            # emulate the .config object shape used in the function
            self.config = type("C", (), {"use_repo_settings_file": False, "model": "Claude-3-5-Sonnet"})

        def as_dict(self):
            return {}

    # Provide deterministic provider and settings
    monkeypatch.setattr(utils, "get_git_provider_with_context", lambda pr_url: object())
    monkeypatch.setattr(utils, "get_settings", lambda: FakeSettingsNoRepo())

    def fake_set_claude_model():
        called["set_claude"] = True

    monkeypatch.setattr(utils, "set_claude_model", fake_set_claude_model)

    # Run
    apply_repo_settings("http://example.com/pr/1")

    # Assertions: model setter called and env var enforced
    assert called["set_claude"] is True
    assert os.environ["AUTO_CAST_FOR_DYNACONF"] == "false"


def test_apply_repo_settings_repo_settings_apply_and_cleanup_error_round_040(monkeypatch, tmp_path):
    """
    Simulate applying repo settings where:
    - context has no cached repo_settings so git_provider.get_repo_settings() returns bytes
    - Dynaconf first call raises TypeError (older version fallback), then fallback returns a mapping
    - get_settings().set raises to force the error_local handling path
    - os.remove raises to exercise the cleanup-exception logging path

    Verifies handle_configurations_errors is called with an error structure and that the logger recorded the cleanup error.
    """
    # Prepare repo settings bytes that will be written to the temporary file
    repo_bytes = b"[sec_empty]\n\n[sec1]\nnewk=newv\n"

    # Patch context.get to return None so code will call git_provider.get_repo_settings()
    class FakeContext:
        def get(self, key, default=None):
            return None

    monkeypatch.setattr(utils, "context", FakeContext())

    # Fake git provider returning bytes
    class FakeGitProvider:
        def get_repo_settings(self):
            return repo_bytes

    monkeypatch.setattr(utils, "get_git_provider_with_context", lambda pr_url: FakeGitProvider())

    # Fake settings object that raises on set(...) to trigger the outer exception handling
    class FakeSettingsRaiseOnSet:
        def __init__(self):
            self.config = type("C", (), {"use_repo_settings_file": True, "model": "not-claude"})

        def as_dict(self):
            # Existing repo settings section values for copy.deepcopy(get_settings().as_dict().get(section, {}))
            return {"sec1": {"old": "ov"}}

        def unset(self, section):
            # pretend to unset successfully
            unset_calls.append(section)

        def set(self, section, section_dict, merge=False):
            # Force an exception during set to exercise the error_local and handling path
            raise RuntimeError("set failed")

    unset_calls = []
    monkeypatch.setattr(utils, "get_settings", lambda: FakeSettingsRaiseOnSet())

    # Dynaconf behavior: first call with kwargs -> raise TypeError; fallback call without kwargs -> succeed
    class FakeDynaconf:
        def __init__(self, settings_files, **kwargs):
            # When kwargs are present (first-call attempt) simulate older dynaconf by raising TypeError
            if kwargs:
                raise TypeError("unsupported kwargs")
            # On fallback, return an object with as_dict method
            self._data = {"sec_empty": {}, "sec1": {"newk": "newv"}}

        def as_dict(self):
            return self._data

    monkeypatch.setattr(utils, "Dynaconf", FakeDynaconf)

    # Capture calls to handle_configurations_errors
    called_handle = {}

    def fake_handle_configurations_errors(errors, git_provider):
        called_handle["errors"] = errors
        called_handle["git_provider"] = git_provider

    monkeypatch.setattr(utils, "handle_configurations_errors", fake_handle_configurations_errors)

    # Fake logger capturing warnings/errors
    logs = {"warnings": [], "errors": []}

    class FakeLogger:
        def warning(self, *args, **kwargs):
            logs["warnings"].append(" ".join(map(str, args)))

        def error(self, *args, **kwargs):
            logs["errors"].append(" ".join(map(str, args)))

        def debug(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def exception(self, *args, **kwargs):
            pass

    monkeypatch.setattr(utils, "get_logger", lambda: FakeLogger())

    # Force os.remove to raise when cleanup attempts to delete the temporary settings file
    def fake_remove(path):
        raise OSError("failed to remove")

    monkeypatch.setattr(utils.os, "remove", fake_remove)

    # Run the function under test
    apply_repo_settings("http://example.com/pr/2")

    # Assertions: handle_configurations_errors should have been called with an error describing the set failure
    assert "errors" in called_handle
    assert isinstance(called_handle["errors"], list) and len(called_handle["errors"]) >= 1
    # The reported error text should contain the original set exception message we raised
    assert any("set failed" in err.get("error", "") for err in called_handle["errors"]) or any(
        "set failed" in str(err) for err in called_handle["errors"]
    )

    # The cleanup failure should have been logged as an error
    assert logs["errors"], "Expected an error log entry for failed removal of temp file"
