import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.timer')
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
        """Test reset with a whitespace-padded float minutes string matches regex and sets duration."""
        timer = RDAgentTimer()
        self.assertFalse(timer.started)

        # use a string that includes leading/trailing whitespace and a float with 'm' unit
        timer.reset("  2.5 m  ")

        self.assertTrue(timer.started)
        expected = timedelta(minutes=2.5)
        # all_duration should be set to 2.5 minutes
        self.assertEqual(timer.all_duration, expected)

        # target_time should be roughly now + expected (allow small timing drift)
        remaining_seconds = (timer.target_time - datetime.now()).total_seconds()
        self.assertAlmostEqual(remaining_seconds, expected.total_seconds(), delta=0.5)
