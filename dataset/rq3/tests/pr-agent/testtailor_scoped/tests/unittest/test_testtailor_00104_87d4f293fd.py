import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.utils')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Exercise the Dynaconf try/except branch inside apply_repo_settings by
        forcing the first Dynaconf call to raise TypeError (simulating an older
        Dynaconf that doesn't accept the security kwargs) and allowing the
        fallback Dynaconf call to succeed. Verify repo settings were applied
        (merged) into the current settings object.
        """
        # Prepare fake settings object
        class FakeConfig:
            def __init__(self):
                self.use_repo_settings_file = True
                self.model = "gpt-4"  # not the special claude marker

        class FakeSettings:
            def __init__(self):
                # initial content in settings to verify merging behavior
                self._store = {"core": {"existing": "old"}}
                self.config = FakeConfig()

            def as_dict(self):
                return copy.deepcopy(self._store)

            def unset(self, section):
                self._store.pop(section, None)

            def set(self, section, section_dict, merge=False):
                # mimic the Dynaconf set used in the code path
                self._store[section] = copy.deepcopy(section_dict)

        fake_settings = FakeSettings()

        # Fake Dynaconf: first call (with the security kwargs present) raises TypeError,
        # second call (only settings_files) succeeds and returns a fake settings object.
        class FakeDynaconf:
            def __init__(self, *args, **kwargs):
                # if security-related kwargs are present simulate older Dynaconf -> TypeError
                bad_keys = {"load_dotenv", "merge_enabled", "envvar_prefix", "core_loaders", "loaders"}
                if set(kwargs.keys()) & bad_keys:
                    raise TypeError("fake dynaconf refuses these kwargs")
                # otherwise simulate loaded settings from the repo file
                # emulate what Dynaconf.as_dict() would return after parsing the repo toml
                self._data = {"core": {"repo_key": "value_from_repo"}}

            def as_dict(self):
                return copy.deepcopy(self._data)

        # Fake git provider that returns a small TOML content as bytes
        class FakeGitProvider:
            def get_repo_settings(self):
                return b'[core]\nrepo_key = "value_from_repo"\n'

            # Not expected to be called in this test path, but provide no-op methods
            def is_supported(self, _):
                return False

        # Patch the names used by apply_repo_settings by manipulating its globals
        func = apply_repo_settings
        g = func.__globals__

        # Save original globals to restore later
        originals = {}
        for name in ("get_settings", "Dynaconf", "get_git_provider_with_context", "context", "handle_configurations_errors"):
            originals[name] = g.get(name, None)

        try:
            # Inject our fakes
            g["get_settings"] = lambda: fake_settings
            g["Dynaconf"] = FakeDynaconf
            g["get_git_provider_with_context"] = lambda pr_url: FakeGitProvider()
            # start with an empty dict-like context
            g["context"] = {}
            # handle_configurations_errors should be present but won't be used for errors in this test
            g["handle_configurations_errors"] = lambda errors, gp: None

            # Run the function under test
            func("http://example.com/pr/1")

            # Verify that the repo settings (from FakeDynaconf.as_dict) were merged into our fake settings
            final = fake_settings.as_dict()
            assert "core" in final, "expected 'core' section in settings after apply_repo_settings"
            assert final["core"].get("repo_key") == "value_from_repo", "repo settings value not applied"
            # existing keys should be preserved (merge behavior)
            assert final["core"].get("existing") == "old", "existing settings were not preserved"
        finally:
            # restore originals
            for name, val in originals.items():
                if val is None:
                    g.pop(name, None)
                else:
                    g[name] = val
