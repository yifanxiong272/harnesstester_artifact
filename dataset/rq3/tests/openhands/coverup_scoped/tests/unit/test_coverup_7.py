# file: openhands/agenthub/dummy_agent/agent.py:107-183
# asked: {"lines": [108, 109, 111, 112, 114, 115, 117, 118, 119, 121, 122, 123, 126, 127, 128, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 145, 147, 148, 149, 151, 153, 155, 156, 158, 159, 161, 162, 163, 164, 165, 167, 168, 170, 171, 172, 173, 174, 176, 178, 179, 180, 183], "branches": [[108, 109], [108, 111], [114, 115], [114, 183], [117, 118], [117, 183], [121, 122], [121, 126], [126, 127], [126, 183], [131, 132], [131, 178], [137, 138], [137, 147], [139, 140], [139, 147], [147, 148], [147, 155], [149, 151], [149, 155], [155, 131], [155, 156], [159, 131], [159, 161], [161, 162], [161, 170], [163, 131], [163, 164], [170, 131], [170, 171], [172, 131], [172, 173], [178, 126], [178, 179]]}
# gained: {"lines": [108, 109, 111, 112, 114, 115, 117, 118, 119, 121, 122, 123, 126, 127, 128, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 145, 147, 148, 149, 151, 153, 155, 156, 158, 159, 161, 162, 163, 164, 165, 167, 168, 170, 171, 172, 173, 174, 176, 178, 179, 180, 183], "branches": [[108, 109], [108, 111], [114, 115], [117, 118], [121, 122], [121, 126], [126, 127], [126, 183], [131, 132], [131, 178], [137, 138], [139, 140], [147, 148], [149, 151], [155, 156], [159, 161], [161, 162], [161, 170], [163, 164], [170, 171], [172, 173], [178, 179]]}

import importlib
import pytest

from openhands.controller.state.state import State

MODULE_PATH = "openhands.agenthub.dummy_agent.agent"


class FakeHistEvent:
    """Marker class for fake history events used in tests."""
    def __init__(self, name="fake"):
        self.name = name


def _patch_dummy_init(monkeypatch, steps):
    """
    Monkeypatch DummyAgent.__init__ so we can instantiate the agent without
    needing full AgentConfig / LLMRegistry wiring. The patched __init__
    will only set the .steps attribute.
    """
    mod = importlib.import_module(MODULE_PATH)
    DummyAgent = getattr(mod, "DummyAgent")

    def fake_init(self, config=None, llm_registry=None):
        # only set required attribute used by step()
        self.steps = steps

    monkeypatch.setattr(DummyAgent, "__init__", fake_init, raising=True)
    return mod, DummyAgent


def _patch_event_to_dict(monkeypatch, module, hist_dict, expected_dict):
    """
    Monkeypatch the event_to_dict function in the module so that:
    - If it receives a FakeHistEvent instance, it returns hist_dict
    - Otherwise it returns expected_dict
    """
    def fake_event_to_dict(ev):
        if isinstance(ev, FakeHistEvent):
            return dict(hist_dict)
        else:
            return dict(expected_dict)

    monkeypatch.setattr(module, "event_to_dict", fake_event_to_dict, raising=True)


def _make_iteration_flag(state, cur_val):
    # Set the iteration_flag.current_value to cur_val
    state.iteration_flag.current_value = cur_val
    return state


def _patch_state_view_property(monkeypatch):
    """
    Replace State.view property with one that returns an instance attribute
    _test_view so tests can set state._test_view = [...]
    """
    def _get_view(self):
        return getattr(self, "_test_view", [])
    monkeypatch.setattr(State, "view", property(_get_view), raising=False)


def _assign_view(state, view_list):
    # assign to the backing attribute used by patched view property
    state._test_view = view_list
    return state


def test_step_returns_finish_action_when_iteration_exceeds(monkeypatch):
    module, DummyAgent = _patch_dummy_init(monkeypatch, steps=[{"action": "only_action"}])

    # Instantiate the DummyAgent (uses our fake __init__)
    agent = DummyAgent(None, None)

    # Create state and set iteration to equal len(steps) to trigger finish branch
    state = State()
    _make_iteration_flag(state, cur_val=len(agent.steps))

    AgentFinishAction = getattr(importlib.import_module("openhands.events.action"), "AgentFinishAction")

    action = agent.step(state)
    assert isinstance(action, AgentFinishAction)


def test_step_normalizes_path_and_message_and_metadata_and_matches(monkeypatch):
    # Prepare expected and hist dicts
    expected_dict = {
        "observation": "file_write",
        "extras": {
            "metadata": {},
            "path": "hello.sh",
        },
        "message": "I wrote to the file hello.sh.",
    }

    hist_dict = {
        "observation": "file_write",
        "id": 999,
        "timestamp": "SOME_TS",
        "cause": "X",
        "source": "Y",
        "extras": {
            "metadata": {
                "pid": 1234,
                "username": "me",
                "hostname": "host",
                "working_dir": "/home/me",
                "py_interpreter_path": "/usr/bin/python",
                "suffix": "_xyz",
                "other": "keep-me"
            },
            "path": "/tmp/subdir/hello.sh",
        },
        "message": "I wrote to the file /tmp/subdir/hello.sh"
    }

    # steps: current index 2, previous index 1 has one expected observation object
    expected_obs_obj = object()
    steps = [
        {"action": "a0", "observations": []},
        {"action": "a1", "observations": [expected_obs_obj]},
        {"action": "a2", "observations": []},
    ]

    module, DummyAgent = _patch_dummy_init(monkeypatch, steps=steps)

    # Patch event_to_dict so it returns our dicts depending on whether the
    # input is our fake history event or the expected_obs_obj.
    _patch_event_to_dict(monkeypatch, module, hist_dict=hist_dict, expected_dict=expected_dict)

    # Patch State.view property so we can set state._test_view
    _patch_state_view_property(monkeypatch)

    # Instantiate agent
    agent = DummyAgent(None, None)

    # Build state: set iteration to 2 to process prev index 1
    state = State()
    _make_iteration_flag(state, cur_val=2)

    # Put a FakeHistEvent in view so hist_events will pick it up
    hist_event = FakeHistEvent()
    _assign_view(state, [hist_event])

    action = agent.step(state)
    assert action == "a2"


def test_step_handles_read_message_normalization_and_mismatch_and_insufficient_history(monkeypatch):
    # Sub-scenario A: mismatch after normalization
    expected_dict_A = {
        "observation": "file_read",
        "extras": {"metadata": {}, "path": "hello.sh"},
        "message": "I read the file hello.sh."
    }
    hist_dict_A = {
        "observation": "file_read",
        "id": 55,
        "timestamp": "TS",
        "extras": {"metadata": {"pid": 1, "username": "u"}, "path": "/var/tmp/other.sh"},
        "message": "I read the file /var/tmp/other.sh"
    }

    # Sub-scenario B: insufficient history
    expected_dict_B = {
        "observation": "cmd_out",
        "extras": {"metadata": {}, "path": ""},
        "message": "Output"
    }
    hist_dict_B = {}

    expected_obs_obj_A = object()
    steps = [
        {"action": "s0", "observations": []},
        {"action": "s1", "observations": []},
        {"action": "s2", "observations": [expected_obs_obj_A]},
        {"action": "s3", "observations": []},
    ]

    module, DummyAgent = _patch_dummy_init(monkeypatch, steps=steps)
    _patch_state_view_property(monkeypatch)
    agent = DummyAgent(None, None)

    # ---- Sub-scenario A: mismatch after normalization ----
    _patch_event_to_dict(monkeypatch, module, hist_dict=hist_dict_A, expected_dict=expected_dict_A)

    stateA = State()
    _make_iteration_flag(stateA, cur_val=3)
    hist_event_A = FakeHistEvent("read-event")
    _assign_view(stateA, [hist_event_A])

    actionA = agent.step(stateA)
    assert actionA == "s3"

    # ---- Sub-scenario B: insufficient history ----
    _patch_event_to_dict(monkeypatch, module, hist_dict=hist_dict_B, expected_dict=expected_dict_B)

    stateB = State()
    _make_iteration_flag(stateB, cur_val=3)
    _assign_view(stateB, [])

    actionB = agent.step(stateB)
    assert actionB == "s3"
