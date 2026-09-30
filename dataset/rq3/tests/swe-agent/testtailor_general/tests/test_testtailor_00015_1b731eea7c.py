import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.remove_unfinished')
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
        """Ensure remove_unfinished runs on an empty base directory without error."""
        tempfile = __import__("tempfile")
        Path = __import__("pathlib").Path
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            # create a regular file so there is something in the directory,
            # but no subdirectories to process
            (base / "some_file.txt").write_text("content")
            # Should complete without raising and return None
            result = remove_unfinished(base, dry_run=True)
            self.assertIsNone(result)
