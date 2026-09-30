import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
        """When user_id is falsy, enable() should call disable(False) and return without enabling providers."""
        class TestAnalytics(Analytics):
            def disable(self, permanently):
                # record calls to disable and delegate to parent
                self._disable_called = True
                self._disable_arg = permanently
                super().disable(permanently)

        ta = TestAnalytics()
        # Ensure any disable call from __init__ doesn't interfere with our check
        ta._disable_called = False
        ta.user_id = None  # Force the branch: not self.user_id

        ta.enable()

        # enable() should have invoked disable(False)
        self.assertTrue(getattr(ta, "_disable_called", False))
        self.assertEqual(getattr(ta, "_disable_arg", None), False)

        # Providers should remain disabled
        self.assertIsNone(ta.mp)
        self.assertIsNone(ta.ph)
