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
        """When user_id is falsy, enable() should call disable(False) and return early."""
        # Patch get_or_create_uuid so __init__ doesn't create a uuid
        with patch.object(Analytics, "get_or_create_uuid", return_value=None):
            # Patch disable to observe calls. __init__ may call disable; reset before testing enable().
            with patch.object(Analytics, "disable") as mock_disable:
                analytics = Analytics()
                # Ensure there's no user_id to trigger the target branch
                analytics.user_id = None

                # Clear any calls that happened during __init__
                mock_disable.reset_mock()

                analytics.enable()

                # enable should call disable(False) once and return early (no providers initialized)
                mock_disable.assert_called_once_with(False)
                self.assertIsNone(analytics.ph)
                self.assertIsNone(analytics.mp)
