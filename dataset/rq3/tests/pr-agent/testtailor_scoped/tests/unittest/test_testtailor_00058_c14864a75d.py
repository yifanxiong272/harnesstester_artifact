import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.file_filter')
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
        """Ensure that when get_settings().ignore.glob is a string it gets stripped and split."""
        # Build a lightweight settings object that triggers the isinstance(glob_setting, str) branch
        class IgnoreObj:
            pass

        ignore_obj = IgnoreObj()
        ignore_obj.regex = []                 # no direct regex patterns
        ignore_obj.glob = "[foo.py]"          # string form that should be stripped and split

        settings_obj = type("SettingsObj", (), {})()
        settings_obj.ignore = ignore_obj
        settings_obj.config = {'ignore_language_framework': []}
        settings_obj.generated_code = {}

        # Patch get_settings in the module where filter_ignored is defined
        mod = filter_ignored.__globals__
        orig_get_settings = mod.get('get_settings', None)
        mod['get_settings'] = (lambda use_context=False: settings_obj)

        try:
            # prepare sample files like GitHub file objects with .filename
            class FileStub:
                def __init__(self, filename):
                    self.filename = filename
                def __repr__(self):
                    return f"FileStub({self.filename!r})"

            files = [FileStub("foo.py"), FileStub("bar.py"), FileStub("dir/foo.py")]

            # call the function under test
            result = filter_ignored(files, platform="github")

            # Expect "foo.py" to be filtered out (pattern "foo.py" matches only that entry)
            result_filenames = [f.filename for f in result]
            self.assertNotIn("foo.py", result_filenames)
            self.assertIn("bar.py", result_filenames)
            self.assertIn("dir/foo.py", result_filenames)
            self.assertEqual(len(result_filenames), 2)
        finally:
            # restore original get_settings (or remove injected one)
            if orig_get_settings is not None:
                mod['get_settings'] = orig_get_settings
            else:
                if 'get_settings' in mod:
                    del mod['get_settings']
