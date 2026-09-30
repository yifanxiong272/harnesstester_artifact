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
        """Ensure apply_repo_settings writes the repo settings, loads them via Dynaconf,
        and applies the merged section into settings (exercises the tempfile write path)."""
        # Minimal fake settings object that behaves like Dynaconf enough for the code under test
        class FakeSettings:
            def __init__(self):
                # config must expose use_repo_settings_file = True so the code path is taken
                class _Cfg:
                    pass
                self.config = _Cfg()
                self.config.use_repo_settings_file = True
                self.config.model = "gpt-test"
                # as_dict returns an existing section that will be merged with repo settings
                self._base = {"local": {"key": "original"}}
                self._applied = {}
                self.set_calls = []

            def as_dict(self):
                # return a shallow copy to mimic Dynaconf behavior
                return dict(self._base)

            def unset(self, section):
                # mimic Dynaconf unset (remove section) - no-op on base, track applied removals
                if section in self._applied:
                    del self._applied[section]

            def set(self, section, section_dict, merge=False):
                # record the applied section for assertions
                self._applied[section] = section_dict
                self.set_calls.append((section, section_dict, merge))

        # Fake GitProvider that returns a valid TOML content as bytes
        class FakeProvider:
            def __init__(self, pr_url=None):
                self.pr_url = pr_url
                self.published = None

            def get_repo_settings(self):
                # TOML with a section "local" and a new key "newkey"
                return b"[local]\nnewkey = 'new'\n"

            def is_supported(self, feature):
                return False

            def publish_persistent_comment(self, *args, **kwargs):
                self.published = True

            def publish_comment(self, *args, **kwargs):
                self.published = True

        # Fake Dynaconf that reads nothing from disk (we'll just return the parsed dict)
        class FakeDynaconf:
            def __init__(self, *args, **kwargs):
                # accept any signature used by apply_repo_settings
                pass

            def as_dict(self):
                # Reflects what would be parsed from the TOML provided by FakeProvider
                return {"local": {"newkey": "new"}}

        fake_settings = FakeSettings()
        fake_provider = FakeProvider("http://example.com/pr/1")

        # Monkeypatch the names used inside the target function by manipulating its globals
        globs = apply_repo_settings.__globals__
        orig_get_git = globs.get("get_git_provider_with_context")
        orig_get_settings = globs.get("get_settings")
        orig_Dynaconf = globs.get("Dynaconf")
        try:
            globs["get_git_provider_with_context"] = lambda pr_url: fake_provider
            globs["get_settings"] = lambda use_context=False: fake_settings
            globs["Dynaconf"] = FakeDynaconf

            # Call the function under test; this should take the branch that writes the repo settings
            apply_repo_settings("http://example.com/pr/1")

            # Verify that settings.set was called for section 'local' with merged values
            self.assertTrue(len(fake_settings.set_calls) >= 1, "expected at least one set() call")
            # Find the set call for 'local'
            found = None
            for sec, sec_dict, mflag in fake_settings.set_calls:
                if sec == "local":
                    found = (sec, sec_dict, mflag)
                    break
            self.assertIsNotNone(found, "expected a set() call for section 'local'")
            section, section_dict, merge_flag = found
            # original 'key' should be preserved and 'newkey' should be added from repo settings
            expected = {"key": "original", "newkey": "new"}
            self.assertEqual(section_dict, expected)
            self.assertFalse(merge_flag)
        finally:
            # restore original globals to avoid side-effects on other tests
            if orig_get_git is not None:
                globs["get_git_provider_with_context"] = orig_get_git
            else:
                globs.pop("get_git_provider_with_context", None)
            if orig_get_settings is not None:
                globs["get_settings"] = orig_get_settings
            else:
                globs.pop("get_settings", None)
            if orig_Dynaconf is not None:
                globs["Dynaconf"] = orig_Dynaconf
            else:
                globs.pop("Dynaconf", None)
