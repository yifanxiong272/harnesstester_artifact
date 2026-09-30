import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.rate_limiter')
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
        """Ensure GlobalRateLimiter.__init__ returns early when already initialized."""
        # Reset singleton state to ensure a clean start
        GlobalRateLimiter._instance = None
        GlobalRateLimiter._lock = None

        # First instantiation performs initialization
        limiter = GlobalRateLimiter()
        self.assertTrue(limiter._initialized)

        # Mutate attributes to non-default values to detect re-initialization
        limiter.last_request_time = 123.456
        limiter.rate_limit_delay = 7.89

        # Call __init__ again — expected to return immediately due to self._initialized being True
        limiter.__init__()

        # Verify that attributes were not reset by the second __init__ call
        self.assertEqual(limiter.last_request_time, 123.456)
        self.assertEqual(limiter.rate_limit_delay, 7.89)
        self.assertTrue(limiter._initialized)
