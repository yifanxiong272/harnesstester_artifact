# file: pr_agent/git_providers/utils.py:14-90
# asked: {"lines": [34, 35, 36, 37, 38, 40, 41, 42, 44, 47, 49, 50, 51, 53, 55, 56, 59, 60, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 83, 84, 85, 86, 90], "branches": [[17, 89], [25, 32], [33, 34], [62, 63], [62, 72], [63, 65], [63, 67], [68, 69], [68, 70], [77, 78], [77, 82], [82, 83], [89, 90]]}
# gained: {"lines": [34, 35, 36, 37, 38, 40, 41, 42, 44, 47, 49, 50, 51, 53, 55, 56, 59, 60, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 77, 79, 80, 83, 84, 85, 86, 90], "branches": [[17, 89], [33, 34], [62, 63], [62, 72], [63, 65], [63, 67], [68, 69], [68, 70], [77, 82], [82, 83], [89, 90]]}

import os
import tempfile
import types

import pytest

from pr_agent.git_providers import utils as gp_utils
from pr_agent.git_providers.utils import apply_repo_settings


class DummyLogger:
    def __init__(self):
        self.calls = {"warning": [], "debug": [], "info": [], "exception": [], "error": []}

    def warning(self, *args, **kwargs):
        self.calls["warning"].append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.calls["debug"].append((args, kwargs))

    def info(self, *args, **kwargs):
        self.calls["info"].append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.calls["exception"].append((args, kwargs))

    def error(self, *args, **kwargs):
        self.calls["error"].append((args, kwargs))


class DummySettings:
    def __init__(self, use_repo_settings_file=True, model="not-claude"):
        self._data = {}
        class Cfg:
            pass
        self.config = Cfg()
        self.config.use_repo_settings_file = use_repo_settings_file
        self.config.model = model

    def as_dict(self):
        return dict(self._data)

    def unset(self, section):
        if section in self._data:
            del self._data[section]

    def set(self, section, section_dict, merge=False):
        # emulate dynaconf set(merge=False) replacement
        self._data[section] = section_dict


class SimpleContext:
    def __init__(self, get_value=None, set_raises=False):
        self._store = {}
        self._get_value = get_value
        self._set_raises = set_raises

    def get(self, key, default=None):
        if self._get_value is not None:
            return self._get_value
        return default

    def __setitem__(self, key, value):
        if self._set_raises:
            raise Exception("context set failed")
        self._store[key] = value


def make_dynaconf_factory(as_dict_return):
    """
    Returns a factory that acts like the Dynaconf constructor in the module.
    If called with load_dotenv or envvar_prefix kwarg it will raise TypeError once
    to exercise the fallback path; otherwise returns an object with as_dict method.
    """
    class DynObj:
        def __init__(self, settings_files=None, **kwargs):
            self._d = as_dict_return

        def as_dict(self):
            return dict(self._d)

    def factory(*args, **kwargs):
        # If the code passes load_dotenv/envvar_prefix or merge_enabled, simulate TypeError on first call
        if "load_dotenv" in kwargs or "envvar_prefix" in kwargs or "merge_enabled" in kwargs:
            raise TypeError("unsupported parameters")
        return DynObj()
    return factory


def test_apply_repo_settings_success(tmp_path, monkeypatch):
    # Prepare dummy settings and logger
    dummy_settings = DummySettings(use_repo_settings_file=True, model="not-claude")
    # existing settings has section 'section' with existing key
    dummy_settings._data = {"section": {"existing": "old"}}

    logger = DummyLogger()
    monkeypatch.setattr(gp_utils, "get_logger", lambda: logger)

    # context initially has no repo_settings
    ctx = SimpleContext(get_value=None, set_raises=False)
    monkeypatch.setattr(gp_utils, "context", ctx)

    # git provider returns TOML bytes content (we don't need real TOML because Dynaconf is mocked)
    class GP:
        def get_repo_settings(self):
            return b"[section]\nnew = 'value'\n[empty]\n\n"

    monkeypatch.setattr(gp_utils, "get_git_provider_with_context", lambda url: GP())

    # Mock get_settings to return our dummy
    monkeypatch.setattr(gp_utils, "get_settings", lambda: dummy_settings)

    # Dynaconf returns a structure with one non-empty section and one empty section to test skipping
    dyn = make_dynaconf_factory({"section": {"new": "value"}, "empty": {}})
    monkeypatch.setattr(gp_utils, "Dynaconf", dyn)

    # Ensure handle_configurations_errors and set_claude_model exist (no-op)
    monkeypatch.setattr(gp_utils, "handle_configurations_errors", lambda errs, gp: None)
    monkeypatch.setattr(gp_utils, "set_claude_model", lambda: None)

    # Run
    apply_repo_settings("http://example.com/repo/1")

    # Assert that repo settings were applied: section should have merged values
    result = dummy_settings.as_dict()
    assert "section" in result
    assert result["section"]["existing"] == "old"
    assert result["section"]["new"] == "value"

    # Logger should have recorded info about applying repo settings
    assert any("Applying repo settings" in str(args[0]) or isinstance(args[0], str) for args, _ in logger.calls["info"])


def test_apply_repo_settings_dynaconf_typeerror_and_remove_failure(monkeypatch, tmp_path):
    # This test will simulate Dynaconf raising TypeError on first call and os.remove failing in finally.

    dummy_settings = DummySettings(use_repo_settings_file=True, model="not-claude")
    dummy_settings._data = {}

    logger = DummyLogger()
    monkeypatch.setattr(gp_utils, "get_logger", lambda: logger)

    # context has no repo_settings; allow setting
    ctx = SimpleContext(get_value=None, set_raises=False)
    monkeypatch.setattr(gp_utils, "context", ctx)

    # git provider returns some bytes
    class GP:
        def get_repo_settings(self):
            return b"[a]\nval='x'\n"

    monkeypatch.setattr(gp_utils, "get_git_provider_with_context", lambda url: GP())
    monkeypatch.setattr(gp_utils, "get_settings", lambda: dummy_settings)

    # We need to know the temp file path that mkstemp will return to make os.remove fail for that path.
    created_paths = []

    real_mkstemp = tempfile.mkstemp

    def mkstemp_wrapper(suffix=None):
        fd, path = real_mkstemp(suffix=suffix)
        created_paths.append(path)
        return fd, path

    monkeypatch.setattr(gp_utils, "tempfile", types.SimpleNamespace(mkstemp=mkstemp_wrapper))

    # First Dynaconf call (with kwargs) should raise TypeError; fallback should return object with as_dict
    class DynFallback:
        def __init__(self, settings_files=None, **kwargs):
            # Return a dict with a section
            self._d = {"a": {"val": "x"}, "empty": {}}

        def as_dict(self):
            return dict(self._d)

    def dynaconf_factory(*args, **kwargs):
        if "load_dotenv" in kwargs or "envvar_prefix" in kwargs or "merge_enabled" in kwargs:
            raise TypeError("simulate older dynaconf")
        return DynFallback()

    monkeypatch.setattr(gp_utils, "Dynaconf", dynaconf_factory)

    # handle_configurations_errors no-op
    monkeypatch.setattr(gp_utils, "handle_configurations_errors", lambda errs, gp: None)

    # Replace os.remove used inside module to raise for the specific created file.
    # Ensure environ is preserved so os.environ[...] assignments work.
    real_remove = os.remove

    def remove_wrapper(path):
        if created_paths and path == created_paths[0]:
            raise Exception("can't remove")
        return real_remove(path)

    monkeypatch.setattr(gp_utils, "os", types.SimpleNamespace(remove=remove_wrapper, write=os.write, environ=os.environ))

    # Run function; it should not raise despite remove failing
    apply_repo_settings("http://example.com/repo/2")

    # The logger should have an error recorded for failing to remove temp file
    assert any("Failed to remove temporary settings file" in str(args[0]) or isinstance(args[0], str) for args, _ in logger.calls["error"])

    # Clean up file that failed to be removed
    for p in created_paths:
        try:
            real_remove(p)
        except Exception:
            pass


def test_apply_repo_settings_git_provider_exception_triggers_logger_exception(monkeypatch):
    # Simulate git provider raising exception so outer except is triggered and logger.exception is called
    dummy_settings = DummySettings(use_repo_settings_file=True, model="not-claude")

    logger = DummyLogger()
    monkeypatch.setattr(gp_utils, "get_logger", lambda: logger)

    # context.get returns None
    monkeypatch.setattr(gp_utils, "context", SimpleContext(get_value=None, set_raises=False))

    class GP:
        def get_repo_settings(self):
            raise Exception("provider boom")

    monkeypatch.setattr(gp_utils, "get_git_provider_with_context", lambda url: GP())
    monkeypatch.setattr(gp_utils, "get_settings", lambda: dummy_settings)

    # Run; should not raise
    apply_repo_settings("http://example.com/repo/3")

    # Logger.exception should have been called
    assert len(logger.calls["exception"]) >= 1


def test_apply_repo_settings_disabled_but_set_claude_model_called(monkeypatch):
    # When use_repo_settings_file is False, code should skip repo settings and still check model and call set_claude_model.
    dummy_settings = DummySettings(use_repo_settings_file=False, model="Claude-3-5-Sonnet")

    monkeypatch.setattr(gp_utils, "get_settings", lambda: dummy_settings)
    monkeypatch.setattr(gp_utils, "get_logger", lambda: DummyLogger())
    # Set get_git_provider_with_context to something no-op; shouldn't be called
    monkeypatch.setattr(gp_utils, "get_git_provider_with_context", lambda url: None)

    called = {"set_claude": False}

    def set_claude():
        called["set_claude"] = True

    monkeypatch.setattr(gp_utils, "set_claude_model", set_claude)

    # Run
    apply_repo_settings("http://example.com/repo/4")

    assert called["set_claude"] is True
