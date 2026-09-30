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
        """When asked_opt_in is falsy, enable() should call disable(False)
        and not initialize Posthog (ph), leaving mp and ph as None and not
        setting permanently_disable to True.
        """
        # Avoid touching the real filesystem by short-circuiting data file access
        with patch.object(Analytics, "get_data_file_path", return_value=None):
            # Patch Posthog so we can assert it is not constructed
            with patch("aider.analytics.Posthog") as mock_posthog:
                analytics = Analytics()
                # Ensure a user_id exists so enable() reaches the asked_opt_in check
                self.assertIsNotNone(analytics.user_id)

                # Set providers to non-None sentinels so disable(False) clearing is observable
                analytics.mp = object()
                analytics.ph = object()
                analytics.permanently_disable = False
                analytics.asked_opt_in = False  # falsy path we want to test

                analytics.enable()

                # Posthog should not be constructed in this branch
                mock_posthog.assert_not_called()

                # Providers should have been cleared by disable(False)
                self.assertIsNone(analytics.mp)
                self.assertIsNone(analytics.ph)
                # permanently_disable should remain False
                self.assertFalse(bool(analytics.permanently_disable))
                # asked_opt_in remains falsy
                self.assertFalse(bool(analytics.asked_opt_in))
