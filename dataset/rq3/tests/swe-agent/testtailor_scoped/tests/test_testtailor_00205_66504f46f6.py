import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.agents')
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
        """complete the test case here"""
        # Create a RetryAgent object without running its __init__
        ra = object.__new__(RetryAgent)

        # Prepare initial total attempt stats (should start at zero cost)
        ra._total_instance_attempt_stats = InstanceStats()
        ra._attempt_data = []

        # Create a dummy agent with the required interface
        class DummyAgent:
            def __init__(self):
                self.model = type("M", (), {})()
                # give the model.stats an instance_cost we can check after +=
                self.model.stats = InstanceStats()
                self.model.stats.instance_cost = 5.0
                self.saved = False
                self.got = False

            def save_trajectory(self):
                self.saved = True

            def get_trajectory_data(self):
                self.got = True
                return {"trajectory": ["a", "b"], "info": {"note": "dummy"}}

        dummy = DummyAgent()
        ra._agent = dummy

        # Call the target method
        ra._finalize_agent_run()

        # Assertions: save_trajectory and get_trajectory_data were called,
        # attempt data appended, and total stats updated.
        self.assertTrue(dummy.saved, "save_trajectory was not called on agent")
        self.assertTrue(dummy.got, "get_trajectory_data was not called on agent")
        self.assertEqual(len(ra._attempt_data), 1)
        self.assertEqual(ra._attempt_data[0], {"trajectory": ["a", "b"], "info": {"note": "dummy"}})
        # total instance attempt stats should have increased by dummy.model.stats.instance_cost
        self.assertAlmostEqual(ra._total_instance_attempt_stats.instance_cost, 5.0)
