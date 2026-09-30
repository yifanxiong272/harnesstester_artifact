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
        """When permanently_disable is True, enable() should call disable(True)."""
        # Create analytics instance (may attempt to access filesystem in __init__)
        analytics = Analytics()

        # Prevent any file IO during save_data by short-circuiting get_data_file_path
        analytics.get_data_file_path = lambda: None

        # Ensure there's a user id so enable() doesn't early-return
        self.assertIsNotNone(analytics.user_id)

        # Put non-None providers so we can observe they get cleared
        analytics.mp = object()
        analytics.ph = object()

        # Set up state: permanently_disable should trigger disable(True) in enable()
        analytics.permanently_disable = True
        analytics.asked_opt_in = False

        # Act
        analytics.enable()

        # Assert that disable(True) was invoked: providers cleared, flags set
        self.assertIsNone(analytics.mp)
        self.assertIsNone(analytics.ph)
        self.assertTrue(analytics.permanently_disable)
        self.assertTrue(analytics.asked_opt_in)
