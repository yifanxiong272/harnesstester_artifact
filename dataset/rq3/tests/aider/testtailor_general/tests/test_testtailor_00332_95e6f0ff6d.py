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
        """When writing analytics data raises OSError, save_data should call disable(permanently=False)."""
        # Preserve and set asked_opt_in to True so __init__ doesn't call disable early
        prev_asked = Analytics.asked_opt_in
        Analytics.asked_opt_in = True
        try:
            # Prepare a fake data_file whose write_text raises OSError and exists() is False
            fake_file = MagicMock()
            fake_file.exists.return_value = False
            fake_file.write_text.side_effect = OSError("cannot write")

            with patch.object(Analytics, "get_data_file_path", return_value=fake_file):
                with patch.object(Analytics, "disable") as mock_disable:
                    # Creating Analytics triggers get_or_create_uuid -> save_data which will attempt write_text
                    a = Analytics(logfile=None, permanently_disable=False)
                    # Ensure write was attempted and OSError path executed which should call disable
                    fake_file.write_text.assert_called()
                    mock_disable.assert_called_once_with(permanently=False)
        finally:
            Analytics.asked_opt_in = prev_asked
