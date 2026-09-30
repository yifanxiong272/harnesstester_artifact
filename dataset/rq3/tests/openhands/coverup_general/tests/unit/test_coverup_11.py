# file: openhands/agenthub/dummy_agent/agent.py:107-183
# asked: {"lines": [108, 109, 111, 112, 114, 115, 117, 118, 119, 121, 122, 123, 126, 127, 128, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 145, 147, 148, 149, 151, 153, 155, 156, 158, 159, 161, 162, 163, 164, 165, 167, 168, 170, 171, 172, 173, 174, 176, 178, 179, 180, 183], "branches": [[108, 109], [108, 111], [114, 115], [114, 183], [117, 118], [117, 183], [121, 122], [121, 126], [126, 127], [126, 183], [131, 132], [131, 178], [137, 138], [137, 147], [139, 140], [139, 147], [147, 148], [147, 155], [149, 151], [149, 155], [155, 131], [155, 156], [159, 131], [159, 161], [161, 162], [161, 170], [163, 131], [163, 164], [170, 131], [170, 171], [172, 131], [172, 173], [178, 126], [178, 179]]}
# gained: {"lines": [108, 109, 111, 112, 114, 115, 117, 118, 119, 121, 122, 123, 126, 127, 128, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 145, 147, 148, 149, 151, 153, 155, 156, 158, 159, 161, 162, 163, 164, 165, 167, 168, 170, 171, 172, 173, 174, 176, 178, 179, 180, 183], "branches": [[108, 109], [108, 111], [114, 115], [117, 118], [121, 122], [121, 126], [126, 127], [126, 183], [131, 132], [131, 178], [137, 138], [139, 140], [147, 148], [149, 151], [155, 131], [155, 156], [159, 161], [161, 162], [161, 170], [163, 164], [170, 171], [172, 173], [178, 126], [178, 179]]}

import os
import pytest

from openhands.controller.state.state import State
from openhands.events.action import AgentFinishAction
from openhands.agenthub.dummy_agent.agent import DummyAgent
import openhands.agenthub.dummy_agent.agent as dummy_mod
import openhands.events.serialization.event as event_mod


def _make_state_with_iter(iter_value: int) -> State:
    s = State()
    s.iteration_flag.current_value = iter_value
    return s


def _set_state_view(monkeypatch, hist_events):
    # monkeypatch the State.view property to return our hist_events list for the duration of the test
    monkeypatch.setattr(
        State,
        "view",
        property(lambda self: hist_events),
        raising=True,
    )


def _monkeypatch_event_to_dict(monkeypatch, mapping, default=None):
    """
    mapping: dict mapping id(obj) -> dict to return
    default: fallback dict
    This patches both the serialization module and the dummy agent module reference.
    """

    def fake_event_to_dict(ev):
        return mapping.get(id(ev), default if default is not None else {"observation": True, "content": "", "extras": {}})

    monkeypatch.setattr(event_mod, "event_to_dict", fake_event_to_dict, raising=True)
    monkeypatch.setattr(dummy_mod, "event_to_dict", fake_event_to_dict, raising=True)


def test_step_returns_agent_finish_when_iteration_exceeds():
    # Create agent without running its __init__ to avoid extra dependencies
    agent = DummyAgent.__new__(DummyAgent)
    # Set steps to a small list so we can exceed it
    agent.steps = [{"action": "a0", "observations": []}]
    state = _make_state_with_iter(1)  # current_value == len(steps) should trigger finish

    action = DummyAgent.step(agent, state)
    assert isinstance(action, AgentFinishAction)


def test_step_normalizes_metadata_path_and_message_and_matches(monkeypatch):
    # Prepare agent with a previous observation to be checked
    agent = DummyAgent.__new__(DummyAgent)
    expected_obs = object()
    # steps: index 0 (some), index 1 (current step) -> will look at prev index 0
    agent.steps = [
        {"action": "action_prev", "observations": [expected_obs]},  # prev step
        {"action": "action_current", "observations": []},  # current step
        {"action": "action_after", "observations": []},
    ]
    # We'll set state.iteration_flag.current_value to 1 (current index), so it checks prev at index 0
    state = _make_state_with_iter(1)

    # Create a hist_event that has full path, dynamic metadata and a message with full path.
    hist_event = object()

    # Prepare dicts for event_to_dict to return for both expected and hist events
    expected_dict = {
        # include dynamic keys that will be popped
        "id": -1,
        "timestamp": "2020-01-01T00:00:00",
        "cause": "x",
        "source": "src",
        # observation branch requires 'observation' key
        "observation": True,
        # content and extras - expected has normalized path and message already
        "content": "file content",
        "extras": {
            "metadata": {},  # empty dict (nothing to pop)
            "path": "hello.sh",
        },
        "message": "I wrote to the file hello.sh.",
    }

    hist_dict = {
        "id": 999,
        "timestamp": "2020-02-02T00:00:00",
        "cause": "y",
        "source": "src2",
        "observation": True,
        "content": "file content",
        "extras": {
            "metadata": {
                "pid": 1234,
                "username": "user",
                "hostname": "host",
                "working_dir": "/tmp",
                "py_interpreter_path": "/usr/bin/python",
                "suffix": "sfx",
            },
            "path": "/tmp/hello.sh",
        },
        "message": "I wrote to the file /tmp/hello.sh.",
    }

    mapping = {
        id(expected_obs): expected_dict,
        id(hist_event): hist_dict,
    }

    _monkeypatch_event_to_dict(monkeypatch, mapping)

    # patch State.view to return our single hist_event so hist_events list has length 1
    _set_state_view(monkeypatch, [hist_event])

    # Run step: iteration 1 -> current step is agent.steps[1], action should be "action_current"
    action = DummyAgent.step(agent, state)
    assert action == "action_current"


def test_step_warns_on_short_history_and_mismatch(monkeypatch, capsys):
    # Create agent where previous step has two expected observations, but state.view provides only one -> triggers len(hist_events) < len(expected_observations)
    agent = DummyAgent.__new__(DummyAgent)
    expected_obs1 = object()
    expected_obs2 = object()
    agent.steps = [
        {"action": "act0", "observations": [expected_obs1, expected_obs2]},  # prev step with 2 expected observations
        {"action": "act1", "observations": []},  # current step will be index 1
        {"action": "act2", "observations": []},
    ]

    state = _make_state_with_iter(1)
    # Only one historical event available (short history)
    hist_event = object()

    # Make expected dicts and hist dict such that one of them will mismatch after normalization
    expected_dict1 = {
        "observation": True,
        "content": "first content",
        "extras": {"metadata": {}, "path": "file1.txt"},
    }
    expected_dict2 = {
        "observation": True,
        "content": "second content",
        "extras": {"metadata": {}, "path": "file2.txt"},
    }

    # hist only contains one event corresponding to expected_obs1 but with different content to force a mismatch
    hist_dict = {
        "id": 1,
        "timestamp": "2022-01-01T00:00:00",
        "observation": True,
        "content": "FIRST CONTENT DIFFERENT",
        "extras": {"metadata": {"pid": 111}, "path": "/var/tmp/file1.txt"},
        "message": "I read the file /var/tmp/file1.txt.",
    }

    mapping = {
        id(expected_obs1): expected_dict1,
        id(expected_obs2): expected_dict2,
        id(hist_event): hist_dict,
    }

    _monkeypatch_event_to_dict(monkeypatch, mapping)
    _set_state_view(monkeypatch, [hist_event])  # only one history event, but expected has two

    action = DummyAgent.step(agent, state)
    # Should return current step action (act1)
    assert action == "act1"

    # Capture stdout for warnings
    captured = capsys.readouterr()
    # We expect a warning about expected observations vs got fewer
    assert "Warning: Expected 2 observations, but got 1" in captured.out
    # We also expect a mismatch warning because content differs (after normalization)
    assert "Warning: Observation mismatch. Expected" in captured.out
