import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.request')
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
        """Test is_retryable_error returns True only for HTTPStatusError with 429 status."""
        import httpx

        # Create a response with 429 and capture the raised HTTPStatusError
        req = httpx.Request("GET", "https://example.com")
        resp_429 = httpx.Response(429, request=req)
        try:
            resp_429.raise_for_status()
        except httpx.HTTPStatusError as exc429:
            self.assertTrue(is_retryable_error(exc429))
        else:
            self.fail("Expected HTTPStatusError for 429 response")

        # Create a different HTTPStatusError (non-429) and ensure it is not considered retryable
        resp_500 = httpx.Response(500, request=req)
        try:
            resp_500.raise_for_status()
        except httpx.HTTPStatusError as exc500:
            self.assertFalse(is_retryable_error(exc500))
        else:
            self.fail("Expected HTTPStatusError for 500 response")

        # Non-HTTPStatusError exceptions should return False
        self.assertFalse(is_retryable_error(ValueError("not an httpx error")))
