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
        """When Path.mkdir raises OSError, get_data_file_path should return None and disable analytics."""
        # Prevent __init__ from creating/reading files by no-oping get_or_create_uuid during construction
        with patch.object(Analytics, "get_or_create_uuid", return_value=None):
            a = Analytics(logfile=None)

        # Replace the instance's disable with a wrapped MagicMock so we can assert it was called
        orig_disable = a.disable
        a.disable = MagicMock(wraps=orig_disable)

        # Now patch Path.mkdir to raise OSError and call the method under test
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            result = a.get_data_file_path()

        # Expect None because mkdir raised OSError and the method should disable analytics and return None
        self.assertIsNone(result)

        # disable should have been called from the exception handler
        self.assertTrue(a.disable.called)

        # After disable, analytics providers should be None
        self.assertIsNone(a.mp)
        self.assertIsNone(a.ph)
