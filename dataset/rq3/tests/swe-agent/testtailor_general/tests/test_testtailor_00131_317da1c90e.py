import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.__init__')
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
        """Ensure impose_rex_lower_bound raises RuntimeError when rex version is below minimal."""
        # Replace the get_rex_version function used by impose_rex_lower_bound to return an old version
        original_get_rex = impose_rex_lower_bound.__globals__.get("get_rex_version")
        try:
            impose_rex_lower_bound.__globals__["get_rex_version"] = lambda: "1.0.0"
            with self.assertRaises(RuntimeError) as cm:
                impose_rex_lower_bound()
            msg = str(cm.exception)
            # Check that the error message mentions the old version and upgrade instruction
            self.assertIn("SWE-ReX version 1.0.0 is too old", msg)
            self.assertIn("pip install --upgrade swe-rex", msg)
        finally:
            # Restore original function to avoid side effects on other tests
            if original_get_rex is not None:
                impose_rex_lower_bound.__globals__["get_rex_version"] = original_get_rex
