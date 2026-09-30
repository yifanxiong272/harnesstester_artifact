import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.server')
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
        """When PSUTIL_AVAILABLE is False, get_parent_process_cmdline() returns None."""
        # Patch the function's module-global PSUTIL_AVAILABLE to simulate psutil absence.
        globals_dict = get_parent_process_cmdline.__globals__
        original = globals_dict.get('PSUTIL_AVAILABLE', None)
        try:
            globals_dict['PSUTIL_AVAILABLE'] = False
            result = get_parent_process_cmdline()
            self.assertIsNone(result, "Expected None when PSUTIL_AVAILABLE is False")
        finally:
            # Restore original value to avoid side effects on other tests.
            if original is None:
                globals_dict.pop('PSUTIL_AVAILABLE', None)
            else:
                globals_dict['PSUTIL_AVAILABLE'] = original
