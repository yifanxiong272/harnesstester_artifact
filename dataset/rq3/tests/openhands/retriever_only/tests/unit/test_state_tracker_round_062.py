import types
import pytest

from openhands.controller.state import state_tracker as st


class _DummyEvent:
    def __init__(self, id, hidden=False):
        self.id = id
        self.hidden = hidden


class _FakeAction(_DummyEvent):
    pass


class _FakeObservation(_DummyEvent):
    pass


class _SimpleState:
    def __init__(self, start_id=0, end_id=0):
        self.start_id = start_id
        self.end_id = end_id
        self.history = None


class _DummyStream:
    def __init__(self, events, latest_id=0):
        self._events = list(events)
        self._latest = latest_id

    def search_events(self, start_id, end_id, reverse, filter):
        # Return events that are in the provided list and within id range
        for e in self._events:
            if start_id <= e.id <= end_id:
                yield e

    def get_latest_event_id(self):
        return self._latest


def _make_tracker_with_state(start_id, end_id):
    # avoid calling StateTracker.__init__ by creating object directly
    tracker = object.__new__(st.StateTracker)
    tracker.state = _SimpleState(start_id=start_id, end_id=end_id)
    # agent_history_filter is passed through to search_events; not used by our dummy
    tracker.agent_history_filter = None
    return tracker


def test_init_history_start_id_greater_than_end_round_062():
    """When state.start_id > state.end_id + 1, history should be emptied and function returns early."""
    # prepare a tracker whose start_id is greater than end_id + 1
    tracker = _make_tracker_with_state(start_id=10, end_id=0)

    # event_stream won't be used because end_id >= 0 path is used and function returns early
    stream = _DummyStream(events=[], latest_id=0)

    # Call under test
    result = tracker._init_history(stream)

    # After early return history must be an empty list and result is None
    assert tracker.state.history == []
    assert result is None


def test_init_history_observation_without_action_keeps_event_round_062(monkeypatch):
    """An AgentDelegateObservation without a matching prior AgentDelegateAction is ignored for pairing,
    but the observation remains in the final history when there are no delegate ranges.
    """
    # Patch module-level delegate classes so isinstance checks work predictably
    monkeypatch.setattr(st, "AgentDelegateAction", _FakeAction, raising=False)
    monkeypatch.setattr(st, "AgentDelegateObservation", _FakeObservation, raising=False)

    # Build events: an observation with no preceding action
    obs = _FakeObservation(id=2)
    other = _DummyEvent(id=1)
    events = [other, obs]

    tracker = _make_tracker_with_state(start_id=0, end_id=3)
    stream = _DummyStream(events=events, latest_id=3)

    tracker._init_history(stream)

    # delegate_ranges will be empty because no action preceded the observation
    # The full events list should be preserved as history in original order
    assert tracker.state.history == events
    # start_id on state should be set to the effective start (0)
    assert tracker.state.start_id == 0


def test_init_history_delegate_pair_filters_intervening_events_round_062(monkeypatch):
    """When a delegate action and later observation are paired, events strictly between them
    are excluded; the action and observation themselves are kept, plus any events before or after the range.

    Note: StateTracker._init_history reassigns the local name `start_id` in the loop over delegate ranges,
    so the final state.start_id is set to the last delegate action id. The test asserts that observed behavior.
    """
    monkeypatch.setattr(st, "AgentDelegateAction", _FakeAction, raising=False)
    monkeypatch.setattr(st, "AgentDelegateObservation", _FakeObservation, raising=False)

    # Create events in this sequence: before(0), action(1), middle(2), observation(3), after(4)
    before = _DummyEvent(id=0)
    action = _FakeAction(id=1)
    middle = _DummyEvent(id=2)
    observation = _FakeObservation(id=3)
    after = _DummyEvent(id=4)

    events = [before, action, middle, observation, after]

    tracker = _make_tracker_with_state(start_id=0, end_id=4)
    stream = _DummyStream(events=events, latest_id=4)

    tracker._init_history(stream)

    # Expected: keep 'before', then keep only the action and observation (ids 1 and 3), then keep 'after'
    expected_ids = [e.id for e in [before, action, observation, after]]
    got_ids = [e.id for e in tracker.state.history]
    assert got_ids == expected_ids
    # verify the middle event (id=2) was filtered out
    assert 2 not in got_ids
    # The implementation overwrites the local start_id when iterating delegate ranges,
    # so the final state.start_id is set to the last delegate action id (action.id == 1)
    assert tracker.state.start_id == action.id
