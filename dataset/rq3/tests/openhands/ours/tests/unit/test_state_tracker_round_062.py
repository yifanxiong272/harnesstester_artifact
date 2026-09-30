import types
from types import MethodType
from types import SimpleNamespace
import pytest

import openhands.controller.state.state_tracker as st


class FakeEventStream:
    def __init__(self, events, latest_id=None):
        self._events = list(events)
        self._latest = latest_id if latest_id is not None else (self._events[-1].id if self._events else -1)

    def get_latest_event_id(self):
        return self._latest

    def search_events(self, *, start_id, end_id, reverse=False, filter=None):
        # Return events whose id is between start_id and end_id inclusive, in original order
        for e in self._events:
            if start_id <= e.id <= end_id:
                yield e


def _bind_tracker_method(start_id, end_id, agent_history_filter=None):
    # Create a minimal "self" object that the StateTracker._init_history implementation expects
    self_obj = SimpleNamespace()
    self_obj.state = SimpleNamespace(start_id=start_id, end_id=end_id, history=None)
    self_obj.agent_history_filter = agent_history_filter
    # Bind the real method to our simple object
    bound = MethodType(st.StateTracker._init_history, self_obj)
    return self_obj, bound


def test_start_id_greater_end_round_062(monkeypatch):
    # Cover branch: if start_id > end_id + 1 -> logger.warning, state.history becomes [] and method returns
    self_obj, bound_init = _bind_tracker_method(start_id=5, end_id=0)

    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    # Patch logger.warning so we can assert it was called
    monkeypatch.setattr(st.logger, "warning", fake_warning)

    # Call with event_stream=None because end_id >= 0 path will not call into the stream
    bound_init(None)

    assert isinstance(self_obj.state.history, list)
    assert self_obj.state.history == []
    assert warnings, "Expected a logger.warning call when start_id > end_id + 1"
    assert "start_id 5 is greater than end_id + 1" in warnings[0]


def test_no_delegate_ranges_means_history_is_all_events_round_062(monkeypatch):
    # Cover branch: when there are no delegate action/observation events, self.state.history == events
    # Prepare simple events (none are AgentDelegateAction/AgentDelegateObservation)
    events = [SimpleNamespace(id=0), SimpleNamespace(id=1), SimpleNamespace(id=2)]
    stream = FakeEventStream(events=events, latest_id=2)

    # Ensure module-level AgentDelegateAction/AgentDelegateObservation are defined but won't match our SimpleNamespace events
    class DummyA:
        pass

    class DummyO:
        pass

    monkeypatch.setattr(st, "AgentDelegateAction", DummyA)
    monkeypatch.setattr(st, "AgentDelegateObservation", DummyO)

    self_obj, bound_init = _bind_tracker_method(start_id=0, end_id=2)

    bound_init(stream)

    # History should be the raw events returned by search_events
    assert [e.id for e in self_obj.state.history] == [0, 1, 2]


def test_delegate_pairing_and_unmatched_observation_round_062(monkeypatch):
    # Cover delegate pairing logic including the branch where an observation is found without a matching action
    # Create dummy classes that will be recognized by isinstance in the implementation
    class DummyAction:
        def __init__(self, id):
            self.id = id

    class DummyObservation:
        def __init__(self, id):
            self.id = id

    monkeypatch.setattr(st, "AgentDelegateAction", DummyAction)
    monkeypatch.setattr(st, "AgentDelegateObservation", DummyObservation)

    # Build events: unmatched observation (id=1), matching action (id=2), filler (id=3), matching observation (id=4), post event (id=5)
    unmatched_obs = DummyObservation(1)
    action = DummyAction(2)
    filler = SimpleNamespace(id=3)
    matching_obs = DummyObservation(4)
    post = SimpleNamespace(id=5)

    events = [unmatched_obs, action, filler, matching_obs, post]
    stream = FakeEventStream(events=events, latest_id=5)

    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    monkeypatch.setattr(st.logger, "warning", fake_warning)

    self_obj, bound_init = _bind_tracker_method(start_id=0, end_id=5)

    bound_init(stream)

    # The algorithm should detect one delegate range (2,4). The filtered history should include events with id < 2 (unmatched_obs id=1),
    # then the delegate action and observation (ids 2 and 4), then the remaining events after the delegate range (id 5).
    got_ids = [e.id for e in self_obj.state.history]
    assert got_ids == [1, 2, 4, 5]

    # The unmatched observation should have produced a warning
    assert any("Found AgentDelegateObservation without matching action" in str(w) for w in warnings), (
        "Expected a warning about an unmatched AgentDelegateObservation"
    )
