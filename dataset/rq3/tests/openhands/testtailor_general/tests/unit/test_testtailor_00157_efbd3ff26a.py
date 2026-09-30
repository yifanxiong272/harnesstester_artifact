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
        """Verify is_retryable_error recognizes httpx.HTTPStatusError with 429 only."""
        # Case 1: HTTPStatusError with 429 should be retryable
        req = httpx.Request("GET", "https://example.com")
        resp_429 = httpx.Response(429, request=req)
        exc_429 = httpx.HTTPStatusError("Too Many Requests", request=req, response=resp_429)
        self.assertTrue(is_retryable_error(exc_429), "HTTP 429 should be considered retryable")

        # Case 2: HTTPStatusError with non-429 should NOT be retryable
        resp_500 = httpx.Response(500, request=req)
        exc_500 = httpx.HTTPStatusError("Server Error", request=req, response=resp_500)
        self.assertFalse(is_retryable_error(exc_500), "HTTP 500 should NOT be considered retryable")

        # Case 3: Non-httpx exception should NOT be retryable
        self.assertFalse(is_retryable_error(ValueError("some error")), "Non-HTTPStatusError exceptions are not retryable")
