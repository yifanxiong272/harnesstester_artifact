import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.action_sampler')
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
        """Filter out duplicate actions keeps first occurrence and logs reduction."""
        # Create instance without calling __init__ to avoid needing real config/model/tools
        instance = object.__new__(BinaryTrajectoryComparison)

        # Mock tools with a parse_actions method
        class MockTools:
            def parse_actions(self, pc):
                # return (thought, action)
                return pc.get("thought"), pc.get("action")

        # Mock logger to capture debug calls
        class MockLogger:
            def __init__(self):
                self.called = False
                self.msg = None
                self.args = None

            def debug(self, msg, *args):
                self.called = True
                self.msg = msg
                self.args = args

        instance._tools = MockTools()
        instance._logger = MockLogger()

        # Completions contain a duplicate action "a" (second entry)
        completions = [
            {"thought": "t1", "action": "a", "meta": 1},
            {"thought": "t2", "action": "a", "meta": 2},
            {"thought": "t3", "action": "b", "meta": 3},
        ]

        filtered = instance.filter_duplicates(completions)

        # Expect only the first occurrence of action "a" and the unique "b"
        self.assertEqual(len(filtered), 2)
        self.assertIs(filtered[0], completions[0])
        self.assertIs(filtered[1], completions[2])

        # Logger debug should have been called with original and filtered lengths
        self.assertTrue(instance._logger.called)
        self.assertEqual(instance._logger.args, (len(completions), len(filtered)))
