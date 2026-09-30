import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.oai.backend.deprec')
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
        """ConvManager.__init__ creates the path and stores recent_n correctly."""
        # create a unique temporary-like directory under cwd using id(self) to avoid imports
        base = Path.cwd() / f"tmp_conv_{id(self)}"
        nested = base / "level1" / "level2" / "conv_store"
        # ensure it does not exist yet
        self.assertFalse(nested.exists())

        # pass path as string and a custom recent_n
        mgr = ConvManager(path=str(nested), recent_n=5)

        # path should be created and stored as a Path object
        self.assertTrue(nested.exists())
        self.assertTrue(nested.is_dir())
        self.assertEqual(mgr.path, nested)
        self.assertEqual(mgr.recent_n, 5)

        # initializing again on an existing path should not raise and should update recent_n
        mgr2 = ConvManager(path=nested, recent_n=7)
        self.assertEqual(mgr2.path, nested)
        self.assertEqual(mgr2.recent_n, 7)

        # cleanup created directories (they should be empty)
        try:
            nested.rmdir()
            nested.parent.rmdir()
            nested.parent.parent.rmdir()
            nested.parent.parent.parent.rmdir()
        except Exception:
            # best-effort cleanup; tests should still pass if cleanup fails
            pass
