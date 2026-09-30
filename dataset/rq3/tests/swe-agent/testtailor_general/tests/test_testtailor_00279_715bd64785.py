import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.files')
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
        """Calling load_file on a file with an unsupported extension raises NotImplementedError."""
        filename = f"tmp_{self.__class__.__name__}_{id(self)}.txt"
        with open(filename, "w") as f:
            f.write("dummy")
        try:
            with self.assertRaises(NotImplementedError) as cm:
                load_file(filename)
            self.assertEqual(str(cm.exception), "Unsupported file extension: .txt")
        finally:
            try:
                # use __import__ to avoid adding an import statement at top-level
                __import__("os").unlink(filename)
            except Exception:
                pass
