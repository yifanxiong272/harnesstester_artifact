# file: sweagent/agent/action_sampler.py:158-162
# asked: {"lines": [159, 160, 161, 162], "branches": [[160, 161], [160, 162]]}
# gained: {"lines": [159, 160, 161, 162], "branches": [[160, 161], [160, 162]]}

import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison

def test_format_trajectory_non_empty():
    # Prepare a trajectory with two steps
    trajectory = [
        {"action": "a1", "observation": "o1"},
        {"action": "a2", "observation": "o2"},
    ]

    # Call the unbound method; it does not use 'self' so None is fine
    formatted = BinaryTrajectoryComparison._format_trajectory(None, trajectory)

    expected = "Action 0: a1\n Observation 0: o1\nAction 1: a2\n Observation 1: o2"
    assert isinstance(formatted, str)
    assert formatted == expected

def test_format_trajectory_empty():
    # An empty trajectory should produce an empty string
    trajectory = []
    formatted = BinaryTrajectoryComparison._format_trajectory(None, trajectory)
    assert isinstance(formatted, str)
    assert formatted == ""
