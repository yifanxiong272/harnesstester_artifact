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
        """Ensure enable() calls disable(False) when asked_opt_in is falsy but user_id exists."""
        analytics = Analytics()
        # Ensure a user_id exists so the first 'if not self.user_id' check is False
        self.assertIsNotNone(analytics.user_id)
        old_uuid = analytics.user_id

        # Ensure we are not permanently disabled and that asked_opt_in is falsy to trigger the target branch
        analytics.permanently_disable = False
        analytics.asked_opt_in = False

        # Populate providers so disable(False) will clear them
        analytics.mp = "SENTINEL_MP"
        analytics.ph = "SENTINEL_PH"

        # Call enable() which should detect not asked_opt_in and call disable(False) then return
        analytics.enable()

        # After enable(), providers should be cleared and not permanently disabled
        self.assertIsNone(analytics.mp)
        self.assertIsNone(analytics.ph)
        self.assertNotEqual(analytics.permanently_disable, True)
        # user_id should remain unchanged
        self.assertEqual(analytics.user_id, old_uuid)
