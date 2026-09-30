import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.io')
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
        """Verify restore_multiline resets multiline_mode on success and on exception."""

        # Create a small host class that uses the restore_multiline decorator
        class Dummy:
            def __init__(self, start_mode=True):
                self.multiline_mode = start_mode
                # placeholders to observe state inside the wrapped function
                self.inside_mode = None
                self.inside_mode_exc = None

            @restore_multiline
            def do_something(self, x):
                # capture the value of multiline_mode while the wrapped function runs
                self.inside_mode = self.multiline_mode
                return x + 1

            @restore_multiline
            def will_raise(self):
                self.inside_mode_exc = self.multiline_mode
                raise ValueError("intentional")

        # Case 1: start with True, normal return -> should be restored to True
        d = Dummy(start_mode=True)
        self.assertTrue(d.multiline_mode)
        result = d.do_something(4)
        self.assertEqual(result, 5)
        # inside the wrapped function, multiline_mode should have been False
        self.assertFalse(d.inside_mode)
        # after return, original value should be restored
        self.assertTrue(d.multiline_mode)

        # Case 2: start with False, exception -> should be restored to False
        d2 = Dummy(start_mode=False)
        self.assertFalse(d2.multiline_mode)
        with self.assertRaises(ValueError):
            d2.will_raise()
        # inside the wrapped function, multiline_mode should have been False
        self.assertFalse(d2.inside_mode_exc)
        # after exception, original value should be restored
        self.assertFalse(d2.multiline_mode)
