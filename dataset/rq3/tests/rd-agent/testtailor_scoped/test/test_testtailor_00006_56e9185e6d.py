import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.app')
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
        """Verify filter_log_folders returns sorted relative folder paths and excludes files."""
        # use __import__ to avoid adding import statements at top-level
        tempfile = __import__('tempfile')
        Path = __import__('pathlib').Path

        with tempfile.TemporaryDirectory() as td:
            main = Path(td)
            # create directories in non-sorted order
            (main / 'b').mkdir()
            (main / 'a').mkdir()
            (main / 'c').mkdir()
            # create files that should be ignored
            (main / 'file.txt').write_text('ignore me')
            (main / 'd').write_text('also a file, not a directory')

            result = filter_log_folders(main)
            expected = [Path('a'), Path('b'), Path('c')]
            self.assertEqual(result, expected)
