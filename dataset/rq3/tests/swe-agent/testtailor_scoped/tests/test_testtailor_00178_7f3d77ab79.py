import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.models')
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
        """Verify that InstanceStats.__sub__ subtracts each model field correctly and returns an InstanceStats."""
        # Create two InstanceStats with known values
        a = InstanceStats(instance_cost=10.5, tokens_sent=100, tokens_received=50, api_calls=7)
        b = InstanceStats(instance_cost=2.25, tokens_sent=30, tokens_received=60, api_calls=3)

        # Perform subtraction (this should exercise the target dict-comprehension path)
        result = a - b

        # Result must be an InstanceStats
        self.assertIsInstance(result, InstanceStats)

        # Check numeric results
        self.assertAlmostEqual(result.instance_cost, 10.5 - 2.25)
        self.assertEqual(result.tokens_sent, 100 - 30)
        self.assertEqual(result.tokens_received, 50 - 60)  # negative result expected
        self.assertEqual(result.api_calls, 7 - 3)

        # Ensure original operands were not mutated
        self.assertEqual(a.instance_cost, 10.5)
        self.assertEqual(b.instance_cost, 2.25)
