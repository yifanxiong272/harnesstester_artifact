import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.utils')
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
        """Verify _async_raise calls PyThreadState_SetAsyncExc with expected args when exctype is a class"""
        tid = 42
        exctype = RuntimeError

        # Patch the C-API call so we don't actually try to raise in a real thread.
        with unittest.mock.patch.object(ctypes.pythonapi, "PyThreadState_SetAsyncExc", return_value=1) as mock_api:
            result = _async_raise(tid, exctype)

            # Function should return normally (None) when the patched API reports success (res == 1)
            self.assertIsNone(result)

            # Ensure the C-API was called exactly once
            mock_api.assert_called_once()
            call_args = mock_api.call_args[0]
            # First arg should be a ctypes.c_long with the tid value
            self.assertIsInstance(call_args[0], ctypes.c_long)
            self.assertEqual(call_args[0].value, tid)
            # Second arg should be a ctypes.py_object wrapping the exception type
            self.assertIsInstance(call_args[1], ctypes.py_object)
            self.assertIs(call_args[1].value, exctype)
