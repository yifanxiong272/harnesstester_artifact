import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.report')
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
        """Find and call get_os_info() in the aider package and verify its output."""
        import importlib
        import pkgutil
        import platform
        import aider

        expected = f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})"

        # First check the package module itself
        if hasattr(aider, "get_os_info") and callable(getattr(aider, "get_os_info")):
            self.assertEqual(aider.get_os_info(), expected)
            return

        # Walk submodules to find get_os_info
        for finder, name, ispkg in pkgutil.walk_packages(aider.__path__, prefix=aider.__name__ + "."):
            try:
                mod = importlib.import_module(name)
            except Exception:
                # skip modules that fail to import
                continue
            if hasattr(mod, "get_os_info") and callable(getattr(mod, "get_os_info")):
                self.assertEqual(mod.get_os_info(), expected)
                return

        self.fail("get_os_info() not found in the aider package")
