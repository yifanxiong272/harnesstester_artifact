import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skills.views')
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
        """Test that MissingCookieException stores attributes and message correctly"""
        cookie_name = "sessionid"
        cookie_description = "Set this cookie by logging in"
        exc = MissingCookieException(cookie_name, cookie_description)

        # attributes set on the instance
        self.assertEqual(exc.cookie_name, cookie_name)
        self.assertEqual(exc.cookie_description, cookie_description)

        # exception message is formatted as expected
        expected_msg = f"Missing required cookie '{cookie_name}': {cookie_description}"
        self.assertEqual(str(exc), expected_msg)

        # it's an Exception subclass
        self.assertIsInstance(exc, Exception)
