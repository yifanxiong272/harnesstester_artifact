import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.paint_order')
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
        """Trigger __post_init__ returning False by creating an invalid Rect (x1 > x2)
        and avoiding frozen dataclass attribute blocking by using object.__setattr__."""
        # Create instance without running dataclass __init__
        r = object.__new__(Rect)
        # Bypass dataclass/frozen __setattr__ by using object.__setattr__
        object.__setattr__(r, "x1", 2.0)
        object.__setattr__(r, "x2", 1.0)  # x1 > x2 violates the invariant
        object.__setattr__(r, "y1", 0.0)
        object.__setattr__(r, "y2", 1.0)
        self.assertFalse(r.__post_init__())
