# file: pr_agent/git_providers/utils.py:14-90
# asked: {"lines": [34, 35, 36, 37, 38, 40, 41, 42, 44, 47, 49, 50, 51, 53, 55, 56, 59, 60, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 83, 84, 85, 86, 90], "branches": [[17, 89], [25, 32], [33, 34], [62, 63], [62, 72], [63, 65], [63, 67], [68, 69], [68, 70], [77, 78], [77, 82], [82, 83], [89, 90]]}
# gained: {"lines": [34, 35, 36, 37, 38, 40, 41, 42, 44, 47, 49, 50, 51, 53, 55, 56, 59, 60, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 77, 83, 84, 85, 86, 90], "branches": [[33, 34], [62, 63], [62, 72], [63, 65], [63, 67], [68, 69], [68, 70], [77, 82], [82, 83], [89, 90]]}

import os
import tempfile
import types

import pytest

import pr_agent.git_providers.utils as utils_mod
from pr_agent.git_providers.utils import apply_repo_settings


class DummyLogger:
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


class GetSettingsStub:
    def __init__(self, model='other-model'):
        # config object with attributes
        self.config = types.SimpleNamespace(use_repo_settings_file=True, model=model)
        # track set/unset calls
        self._storage = {}
        self.set_calls = []
        self.unset_calls = []

    def as_dict(self):
        # Return existing settings; used to seed merging.
        return self._storage.copy()

    def unset(self, section):
        self.unset_calls.append(section)
        self._storage.pop(section, None)

    def set(self, section, value, merge=False):
        self.set_calls.append((section, value, merge))
        self._storage[section] = value


class DynaconfStub:
    """
    Simulates Dynaconf. If instantiated with kwargs that include 'load_dotenv' or
    'envvar_prefix' it will raise TypeError once to trigger the fallback branch.
    Otherwise, returns an object with as_dict() returning a provided mapping.
    """
    # class-level flag to control first-call raising
    raise_on_kwargs = True

    def __init__(self, settings_files=None, **kwargs):
        if kwargs and DynaconfStub.raise_on_kwargs:
            # simulate older Dynaconf that doesn't accept these params
            raise TypeError("unexpected kwargs")
        # store a default mapping or attempt to read a prepared mapping per filename
        # We'll not read the file; tests will rely on replacing the as_dict via attribute
        self._mapping = {}

    def as_dict(self):
        return self._mapping.copy()


class DummyGitProvider:
    def __init__(self, repo_settings_bytes):
        self._repo_settings = repo_settings_bytes
        self.handled_errors = []

    def get_repo_settings(self):
        return self._repo_settings

    # For potential handle_configurations_errors call: capture it if called with provider
    def __repr__(self):
        return "<DummyGitProvider>"


def test_apply_repo_settings_typeerror_fallback_and_set_calls(monkeypatch, tmp_path):
    """
    Test the branch where Dynaconf(...) raises TypeError for the secure kwargs,
    then falls back to the simpler Dynaconf call. Ensure that empty sections are
    skipped and non-empty sections are merged into get_settings via set().
    Also verify that set_claude_model() is called when model matches.
    """

    # Prepare stubs and monkeypatches
    dummy_logger = DummyLogger()
    monkeypatch.setattr(utils_mod, "get_logger", lambda: dummy_logger)

    # get_settings stub with an existing section to test merging behavior
    gs = GetSettingsStub(model="claude-3-5-sonnet")
    # Pre-populate existing section to ensure merging keeps old keys unless overwritten
    gs._storage = {"section": {"old": "keep"}}
    monkeypatch.setattr(utils_mod, "get_settings", lambda: gs)

    # Prepare Dynaconf stub: first instantiation with kwargs raises TypeError,
    # second instantiation (without kwargs) should succeed and provide as_dict mapping.
    DynaconfStub.raise_on_kwargs = True

    def dynaconf_factory(*args, **kwargs):
        # args[0] corresponds to settings_files=[repo_settings_file] typically
        inst = DynaconfStub(*args, **kwargs)
        # Provide the mapping that includes an empty section and a filled one
        inst._mapping = {"empty": {}, "section": {"k": "v"}}
        return inst

    monkeypatch.setattr(utils_mod, "Dynaconf", dynaconf_factory)

    # Prepare git provider that returns TOML bytes (actual content is not parsed because Dynaconf is stubbed)
    git_provider = DummyGitProvider(repo_settings_bytes=b'[empty]\n\n[section]\nk = "v"\n')
    monkeypatch.setattr(utils_mod, "get_git_provider_with_context", lambda url: git_provider)

    # Make context.get raise to exercise the inner except path that sets repo_settings=None
    class BadContext:
        def get(self, *a, **k):
            raise RuntimeError("boom")

        def __setitem__(self, k, v):
            # emulate context assignment, but allow it silently
            pass

    monkeypatch.setattr(utils_mod, "context", BadContext())

    # Spy for set_claude_model
    called = {"flag": False}

    def fake_set_claude_model():
        called["flag"] = True

    monkeypatch.setattr(utils_mod, "set_claude_model", fake_set_claude_model)

    # Ensure handle_configurations_errors is present (should not be called in this test)
    monkeypatch.setattr(utils_mod, "handle_configurations_errors", lambda errors, gp: gp.handled_errors.append(errors))

    # Call the function under test
    apply_repo_settings("http://example.com/repo/pr/1")

    # Assertions:
    # - Dynaconf fallback should have produced mapping and set() should have been called for "section"
    assert any(call[0] == "section" for call in gs.set_calls), "Expected 'section' to be set in get_settings"
    # Verify merge flag was False when set was called
    matched = [call for call in gs.set_calls if call[0] == "section"]
    assert matched, "No set call recorded for 'section'"
    section_name, section_value, merge_flag = matched[0]
    assert merge_flag is False
    # The merged dict should contain the original key and the new one
    assert section_value["old"] == "keep"
    assert section_value["k"] == "v"

    # Ensure the warning about Dynaconf fallback was logged
    assert dummy_logger.warnings, "Expected a warning logged about Dynaconf TypeError fallback"

    # Ensure set_claude_model was called due to model equal to 'claude-3-5-sonnet'
    assert called["flag"] is True


def test_apply_repo_settings_tempfile_remove_failure_logs_error(monkeypatch):
    """
    Test that when removing the temporary settings file fails, the function logs an error.
    This hits the finally block where os.remove raises and get_logger().error is called.
    """

    dummy_logger = DummyLogger()
    monkeypatch.setattr(utils_mod, "get_logger", lambda: dummy_logger)

    # get_settings stub with a model that does not trigger set_claude_model
    gs = GetSettingsStub(model="not-claude")
    monkeypatch.setattr(utils_mod, "get_settings", lambda: gs)

    # Dynaconf that works normally (does not raise on kwargs)
    DynaconfStub.raise_on_kwargs = False

    def dynaconf_factory_ok(*args, **kwargs):
        inst = DynaconfStub(*args, **kwargs)
        # a mapping that will be skipped entirely (empty) to avoid touching set/unset
        inst._mapping = {"only_empty": {}}
        return inst

    monkeypatch.setattr(utils_mod, "Dynaconf", dynaconf_factory_ok)

    # Git provider returns valid settings bytes
    git_provider = DummyGitProvider(repo_settings_bytes=b'[only_empty]\n')
    monkeypatch.setattr(utils_mod, "get_git_provider_with_context", lambda url: git_provider)

    # Normal context that returns None so git_provider.get_repo_settings() is used
    class GoodContext(dict):
        def get(self, *a, **k):
            return None

    monkeypatch.setattr(utils_mod, "context", GoodContext())

    # Monkeypatch os.remove to raise to simulate failure in cleanup
    def fake_remove(path):
        raise OSError("cannot remove")

    monkeypatch.setattr(os, "remove", fake_remove)

    # Ensure handle_configurations_errors is a no-op
    monkeypatch.setattr(utils_mod, "handle_configurations_errors", lambda errors, gp: None)

    # Call the function under test. It should not raise, but should log an error about remove failure.
    apply_repo_settings("http://example.com/another/repo/pr/2")

    # Assert that an error was logged for failed removal
    assert dummy_logger.errors, "Expected an error log entry when os.remove raises"
    # Ensure no exceptions were recorded (function should handle internally)
    assert not dummy_logger.exceptions, "No exception should bubble up; function should handle it internally"
