import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_polling')
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
    def test_case_01(self):
        """Verify now() returns an ISO 8601 UTC timestamp ending with 'Z' and is close to current UTC time."""
        ts = now()
        # should be a string and end with 'Z' (UTC designator after replacement)
        self.assertIsInstance(ts, str)
        self.assertTrue(ts.endswith("Z"), f"timestamp does not end with Z: {ts}")

        # Replace 'Z' with '+00:00' so datetime.fromisoformat can parse it
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        # parsed datetime should be timezone-aware and in UTC
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset(), timezone.utc.utcoffset(parsed))

        # parsed time should be very close to now in UTC (within 2 seconds)
        now_utc = datetime.now(timezone.utc)
        delta = abs((now_utc - parsed).total_seconds())
        self.assertLess(delta, 2, f"parsed time {parsed} differs from now {now_utc} by {delta} seconds")
