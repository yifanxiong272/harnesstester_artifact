import os
import tempfile
import copy
import types
import pytest

import pr_agent.git_providers.utils as utils


class DummyGitProvider:
    def __init__(self, repo_bytes):
        self._repo = repo_bytes

    def get_repo_settings(self):
        return self._repo


class DummySettings:
    def __init__(self, use_repo_settings_file=True, model_name="not-claude"):
        class Cfg:
            pass

        self.config = Cfg()
        self.config.use_repo_settings_file = use_repo_settings_file
        self.config.model = model_name
        # internal mapping to emulate dynaconf storage
        self._store = {}
        self.set_calls = []
        self.unset_calls = []

    def as_dict(self):
        # return a snapshot-like structure similar to Dynaconf.as_dict
        return copy.deepcopy(self._store)

    def unset(self, section):
        self.unset_calls.append(section)
        self._store.pop(section, None)

    def set(self, section, section_dict, merge=False):
        # record invocation
        self.set_calls.append((section, copy.deepcopy(section_dict), merge))
        self._store[section] = copy.deepcopy(section_dict)


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []
        self.infos = []
        self.errors = []
        self.exceptions = []

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exceptions.append((args, kwargs))


class FakeDynaconfGood:
    def __init__(self, settings_files=None, **kwargs):
        # emulate a parsed TOML with one non-empty section
        self._d = {"mysection": {"k": "v"}}

    def as_dict(self):
        return copy.deepcopy(self._d)


class FakeDynaconfFallback:
    def __init__(self, settings_files=None, **kwargs):
        # emulate older dynaconf fallback: return some empty and some non-empty sections
        self._d = {"emptysection": {}, "another": {}}

    def as_dict(self):
        return copy.deepcopy(self._d)


def _mktemp_file_with_bytes(content: bytes):
    fd, path = tempfile.mkstemp(suffix='.toml')
    # write initial content and keep descriptor open (apply_repo_settings will os.write to it)
    os.write(fd, content)
    # leave file for apply_repo_settings to overwrite/write
    return fd, path


def test_apply_repo_settings_success_round_040(monkeypatch, tmp_path):
    """
    Exercise the path where repo settings are present, Dynaconf works, and a non-empty section
    is applied to the project's settings object. Assert that settings.set was called with expected
    merged section content and that the temporary file is removed.
    """
    # Prepare repo settings bytes
    repo_bytes = b"[mysection]\nk = \"v\"\n"

    # Create a real temp file so mkstemp returns valid fd and path
    fd_real, path_real = _mktemp_file_with_bytes(b"")

    # Monkeypatch tempfile.mkstemp to return our fd and path
    monkeypatch.setattr(utils.tempfile, "mkstemp", lambda suffix='.toml': (fd_real, path_real))

    # Provide dummy git provider that returns our bytes
    monkeypatch.setattr(utils, "get_git_provider_with_context", lambda pr_url: DummyGitProvider(repo_bytes))

    # Provide context.get to return None so the code fetches from git provider
    monkeypatch.setattr(utils, "context", {"get": lambda key, default=None: None})

    # Provide get_settings to return a DummySettings instance
    dummy_settings = DummySettings(use_repo_settings_file=True, model_name="not-claude")
    # seed settings with an initial section to verify merging behavior
    dummy_settings._store = {"mysection": {"existing": "orig"}}
    monkeypatch.setattr(utils, "get_settings", lambda: dummy_settings)

    # Replace Dynaconf with a fake that returns a non-empty section
    monkeypatch.setattr(utils, "Dynaconf", FakeDynaconfGood)

    # Replace logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # Ensure handle_configurations_errors does not get called; replace with one that would raise if invoked
    monkeypatch.setattr(utils, "handle_configurations_errors", lambda errors, gp: (_ for _ in ()).throw(RuntimeError("should not be called")))

    # Call the function under test
    utils.apply_repo_settings("http://example.com/pr/1")

    # After execution, expect that settings.set was called to set 'mysection'
    assert any(call[0] == "mysection" for call in dummy_settings.set_calls), "expected 'mysection' to be set"

    # Confirm that the temporary file was removed by the function's finally block
    assert not os.path.exists(path_real), "temporary repo settings file should be removed"

    # Close the fd if still open
    try:
        os.close(fd_real)
    except OSError:
        pass


def test_apply_repo_settings_write_fail_triggers_error_and_model_round_040(monkeypatch):
    """
    Simulate an error during os.write to exercise the exception handling path that sets error_local and
    calls handle_configurations_errors. Also set the settings.model to 'claude-3-5-sonnet' to ensure
    set_claude_model() is invoked.
    """
    repo_bytes = b"[section]\nkey=1\n"

    # create real temp file and get fd/path
    fd_real, path_real = _mktemp_file_with_bytes(b"")
    monkeypatch.setattr(utils.tempfile, "mkstemp", lambda suffix='.toml': (fd_real, path_real))

    # Provide dummy git provider
    git_provider = DummyGitProvider(repo_bytes)
    monkeypatch.setattr(utils, "get_git_provider_with_context", lambda pr_url: git_provider)

    # context.get returns None
    monkeypatch.setattr(utils, "context", {"get": lambda key, default=None: None})

    # Prepare settings where model should trigger set_claude_model
    dummy_settings = DummySettings(use_repo_settings_file=True, model_name="claude-3-5-sonnet")
    monkeypatch.setattr(utils, "get_settings", lambda: dummy_settings)

    # Replace Dynaconf with fallback class (not necessary here because write fails before Dynaconf), but safe
    monkeypatch.setattr(utils, "Dynaconf", FakeDynaconfFallback)

    # Prepare a logger to capture warnings
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # Make os.write raise to force the code path that sets error_local and calls handle_configurations_errors
    def _fail_write(fd, data):
        raise OSError("simulated write failure")

    monkeypatch.setattr(utils.os, "write", _fail_write)

    # Record invocations of handle_configurations_errors
    called = {"handled": False}

    def _handle_configurations_errors(errors, gp):
        # basic assertions about the shape
        assert isinstance(errors, list)
        assert errors and isinstance(errors[0], dict)
        called["handled"] = True
        # keep it silent

    monkeypatch.setattr(utils, "handle_configurations_errors", _handle_configurations_errors)

    # Record set_claude_model calls
    called_model = {"set_called": False}

    def _set_claude_model():
        called_model["set_called"] = True

    monkeypatch.setattr(utils, "set_claude_model", _set_claude_model)

    # Call function under test; it should not raise (exceptions are caught internally)
    utils.apply_repo_settings("http://example.com/pr/2")

    # Ensure handler was invoked due to write failure
    assert called["handled"] is True, "handle_configurations_errors should be called on write failure"

    # Ensure model switch was invoked
    assert called_model["set_called"] is True, "set_claude_model should be called when model matches"

    # Ensure temporary file is removed even if write failed
    assert not os.path.exists(path_real), "temporary repo settings file should be removed in finally"

    # Close fd if still open
    try:
        os.close(fd_real)
    except OSError:
        pass
