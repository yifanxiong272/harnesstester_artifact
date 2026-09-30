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
        """Simulate PyThreadState_SetAsyncExc returning >1 to force the SystemError branch"""
        tid = 12345
        # save original to restore later
        orig = ctypes.pythonapi.PyThreadState_SetAsyncExc
        calls = []

        def fake_pythreadstate_setasyncexc(c_tid, c_exc):
            # record calls so we can assert on them
            calls.append((c_tid, c_exc))
            # first call simulates "bad" return > 1, subsequent calls behave normally
            return 2 if len(calls) == 1 else 0

        try:
            # replace the C API function with our fake
            ctypes.pythonapi.PyThreadState_SetAsyncExc = fake_pythreadstate_setasyncexc

            # Expect SystemError with the specific message when res != 0 and res != 1
            with self.assertRaisesRegex(SystemError, "PyThreadState_SetAsyncExc failed"):
                _async_raise(tid, SystemExit)

            # Ensure the fake was called at least twice (original call and the revert call)
            self.assertGreaterEqual(len(calls), 2)

            first_tid, first_exc = calls[0]
            second_tid, second_exc = calls[1]

            # Check the tid passed in the first call matches
            # c_tid is a ctypes.c_long instance; check its .value
            self.assertEqual(getattr(first_tid, "value", None), tid)

            # The first exc should be a py_object wrapping the exception type
            if hasattr(first_exc, "value"):
                self.assertIs(first_exc.value, SystemExit)

            # The second call should have been invoked with None to revert the effect
            self.assertIsNone(second_exc)
        finally:
            # restore the original function to avoid side effects on other tests
            ctypes.pythonapi.PyThreadState_SetAsyncExc = orig
