import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.merge_predictions')
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
        """When no .pred files exist in the provided directories, the function should
        log a warning referencing the last directory and not create any output file."""
        # create temporary base directory without using an import statement
        Path = __import__("pathlib").Path
        base = Path(__import__("tempfile").mkdtemp())
        dir1 = base / "one"
        dir2 = base / "two"
        dir1.mkdir()
        dir2.mkdir()

        # grab the logger used inside merge_predictions and patch its warning method
        logger_obj = merge_predictions.__globals__['logger']
        mock_patch = __import__("unittest").mock.patch
        with mock_patch.object(logger_obj, "warning") as mock_warning:
            merge_predictions([dir1, dir2], None)
            # Expect exactly one warning call, with the last directory passed to the function
            mock_warning.assert_called_once_with("No predictions found in %s", dir2)

        # No preds.json should have been created in either directory
        self.assertFalse((dir1 / "preds.json").exists())
        self.assertFalse((dir2 / "preds.json").exists())
