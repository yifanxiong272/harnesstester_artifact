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
        """Ensure apply_repo_settings writes the repo settings to a temp file and
        that the produced Dynaconf instance sees that file contents, and settings
        are merged into the current settings."""
        import sys

        # prepare fake repo settings bytes that would be returned by a git provider
        repo_settings_bytes = b'[config]\nnewkey = "newval"\n'

        # Fake settings object used by get_settings()
        class FakeConfig:
            def __init__(self):
                self.use_repo_settings_file = True
                self.model = "gpt"

        class FakeSettings:
            def __init__(self):
                self.config = FakeConfig()
                # initial state: config section exists with one key
                self._dict = {'config': {'existing': 'old'}}

            def as_dict(self):
                return dict(self._dict)

            def unset(self, section):
                self._dict.pop(section, None)

            def set(self, section, section_dict, merge=False):
                # mirror Dynaconf.set behavior for the test
                self._dict[section] = section_dict

        fake_settings = FakeSettings()

        # Fake GitProvider to return repo settings bytes
        class FakeGitProvider:
            def get_repo_settings(self):
                return repo_settings_bytes

            def is_supported(self, fmt):
                return True

            def publish_persistent_comment(self, *args, **kwargs):
                # no-op for test
                pass

            def publish_comment(self, *args, **kwargs):
                pass

        fake_provider = FakeGitProvider()

        # Prepare a FakeDynaconf that records which file was given and reads its content
        created_instances = []

        class FakeDynaconf:
            def __init__(self, settings_files=None, *args, **kwargs):
                self.settings_files = list(settings_files or [])
                # capture file contents immediately to validate the tempfile write
                self._files_content = []
                for f in self.settings_files:
                    with open(f, 'rb') as fh:
                        self._files_content.append(fh.read())
                created_instances.append(self)

            def as_dict(self):
                # return a parsed-like structure consistent with repo_settings_bytes
                return {'config': {'newkey': 'newval'}}

        # Patch the module where apply_repo_settings is defined
        mod = sys.modules[apply_repo_settings.__module__]
        orig_Dynaconf = getattr(mod, 'Dynaconf', None)
        orig_get_settings = getattr(mod, 'get_settings', None)
        orig_get_git_provider = getattr(mod, 'get_git_provider_with_context', None)

        try:
            # inject fakes
            setattr(mod, 'Dynaconf', FakeDynaconf)
            setattr(mod, 'get_settings', lambda *args, **kwargs: fake_settings)
            setattr(mod, 'get_git_provider_with_context', lambda pr_url: fake_provider)

            # call the function under test
            apply_repo_settings("http://example.com/pr/1")

            # Assertions:
            # 1) FakeDynaconf should have been instantiated once and read the temp file
            assert len(created_instances) >= 1, "Dynaconf was not instantiated"
            inst = created_instances[0]
            assert inst._files_content, "Dynaconf instance did not record any file contents"
            # the tempfile content should match the bytes returned by the git provider
            assert inst._files_content[0] == repo_settings_bytes

            # 2) The fake settings should have been updated with the new key from repo settings
            resulting = fake_settings.as_dict()
            assert 'config' in resulting
            assert resulting['config'].get('newkey') == 'newval'
        finally:
            # restore original attributes to avoid polluting other tests
            if orig_Dynaconf is not None:
                setattr(mod, 'Dynaconf', orig_Dynaconf)
            else:
                delattr(mod, 'Dynaconf')
            if orig_get_settings is not None:
                setattr(mod, 'get_settings', orig_get_settings)
            else:
                delattr(mod, 'get_settings')
            if orig_get_git_provider is not None:
                setattr(mod, 'get_git_provider_with_context', orig_get_git_provider)
            else:
                delattr(mod, 'get_git_provider_with_context')
