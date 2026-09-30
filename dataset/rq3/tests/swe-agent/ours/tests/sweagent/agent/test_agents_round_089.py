import json
import types
import pytest

from sweagent.agent.agents import RetryAgent


class DummyPath:
    def __init__(self):
        self.written = None

    def write_text(self, text):
        # mimic pathlib.Path.write_text signature
        self.written = text
        return None


def make_dummy_agent(data_to_return):
    """Create a minimal dummy object that satisfies RetryAgent.save_trajectory's expectations.

    It provides:
    - get_trajectory_data(self, choose: bool) -> dict
    - _traj_path with write_text(text) method (or None)
    """

    dummy = types.SimpleNamespace()

    def get_trajectory_data(choose: bool):
        # record the passed choose flag for inspection
        dummy._last_choose = choose
        # return a deterministic structure
        return data_to_return

    dummy.get_trajectory_data = get_trajectory_data
    dummy._traj_path = DummyPath()
    return dummy


def test_save_trajectory_writes_and_records_choose_round_089():
    # Prepare deterministic trajectory data
    data = {"step": 1, "note": "ok"}
    dummy = make_dummy_agent(data)

    # Call the function as defined on the class to avoid complex construction
    RetryAgent.save_trajectory(dummy, choose=True)

    # Ensure get_trajectory_data received the choose flag
    assert getattr(dummy, "_last_choose", None) is True

    # The file text should be the json dump with indent=2
    expected = json.dumps(data, indent=2)
    assert dummy._traj_path.written == expected


def test_save_trajectory_asserts_when_no_path_round_089():
    data = {"x": 2}
    dummy = make_dummy_agent(data)
    # simulate missing path
    dummy._traj_path = None

    with pytest.raises(AssertionError):
        RetryAgent.save_trajectory(dummy, choose=False)
