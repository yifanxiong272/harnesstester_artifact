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
        """Ensure that when get_settings().ignore.regex is a string, it's converted to a list
        and matching files are filtered out for the 'github' platform.
        """
        # create a minimal settings object with ignore.regex as a string
        settings = type("S", (), {})()
        settings.ignore = type("I", (), {})()
        settings.ignore.regex = r".*\.md"  # string -> should trigger patterns = [patterns]
        settings.ignore.glob = []  # no additional globs
        settings.config = {"ignore_language_framework": []}
        settings.generated_code = {}

        # simple file-like objects with a .filename attribute (github path handling)
        FileObj = type("FileObj", (), {"__init__": lambda self, fn: setattr(self, "filename", fn)})
        files = [FileObj("Readme.md"), FileObj("main.py")]

        # patch the get_settings used by the module that defines filter_ignored
        with unittest.mock.patch(f"{filter_ignored.__module__}.get_settings", return_value=settings):
            filtered = filter_ignored(files, platform="github")

        # Readme.md should be filtered out by the regex, main.py should remain
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].filename, "main.py")
