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
        """Ensure GlobalRateLimiter.get_lock creates an asyncio.Lock when none exists."""
        # Ensure class-level lock is None to hit the branch
        GlobalRateLimiter._lock = None

        async def _call_get_lock():
            # Call from async context (as intended)
            lock1 = GlobalRateLimiter.get_lock()
            # It should have created an asyncio.Lock instance
            self.assertIsNotNone(lock1)
            self.assertIsInstance(lock1, asyncio.Lock)
            # Subsequent calls should return the same lock instance
            lock2 = GlobalRateLimiter.get_lock()
            self.assertIs(lock1, lock2)

        asyncio.run(_call_get_lock())
