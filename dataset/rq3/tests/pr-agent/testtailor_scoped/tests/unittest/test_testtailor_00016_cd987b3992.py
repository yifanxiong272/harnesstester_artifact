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
        """Ensure string ignore pattern is converted to list and used to filter files (github platform)."""
        # prepare a settings-like object where ignore.regex is a string (triggers isinstance(patterns, str))
        class Ignore:
            def __init__(self, regex, glob):
                self.regex = regex
                self.glob = glob

        class Settings:
            def __init__(self):
                # regex as a string should trigger the branch patterns = [patterns]
                self.ignore = Ignore(r".*utils.py", [])
                self.config = {'ignore_language_framework': []}
                self.generated_code = {}

        settings = Settings()

        # simple file-like objects with a filename attribute (github path handling)
        class FileObj:
            def __init__(self, filename):
                self.filename = filename

        files = [FileObj("my_utils.py"), FileObj("main.py")]

        # patch get_settings used inside filter_ignored to return our settings
        with patch(f"{filter_ignored.__module__}.get_settings", return_value=settings):
            filtered = filter_ignored(files, platform="github")

        # only main.py should remain (my_utils.py matches ".*utils.py" and should be filtered out)
        self.assertEqual([f.filename for f in filtered], ["main.py"])
