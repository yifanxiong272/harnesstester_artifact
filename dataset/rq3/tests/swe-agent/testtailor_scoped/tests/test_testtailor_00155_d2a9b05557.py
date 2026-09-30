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
        """Test BinaryTrajectoryComparison._format_trajectory for empty and non-empty trajectories."""
        # Create an instance without calling __init__ to avoid needing dependencies
        inst = object.__new__(BinaryTrajectoryComparison)

        # Empty trajectory should return an empty string (steps = [] branch exercised)
        res_empty = BinaryTrajectoryComparison._format_trajectory(inst, [])
        self.assertEqual(res_empty, "")

        # Non-empty trajectory should format each step correctly
        traj = [
            {"action": "open_file", "observation": "file opened"},
            {"action": "edit", "observation": "changed line"},
        ]
        res = BinaryTrajectoryComparison._format_trajectory(inst, traj)
        expected = (
            "Action 0: open_file\n Observation 0: file opened\n"
            "Action 1: edit\n Observation 1: changed line"
        )
        self.assertEqual(res, expected)
