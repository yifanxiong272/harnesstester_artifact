import importlib
from types import SimpleNamespace
import pytest


class FakeEvent:
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f"FakeEvent(id={self.id})"


class FakeAction(FakeEvent):
    pass


class FakeObservation(FakeEvent):
    pass


class FakeEventStream:
    def __init__(self, events):
        # events: iterable/list of FakeEvent-like objects
        self._events = list(events)

    def get_latest_event_id(self):
        if not self._events:
            return -1
        return max(e.id for e in self._events)

    def search_events(self, start_id=0, end_id=0, reverse=False, filter=None):
        # Return events whose id is between start_id and end_id inclusive, preserving order
        for e in self._events:
            if start_id <= e.id <= end_id:
                yield e


def _ids(events):
    return [e.id for e in events]


def test_start_id_greater_than_end_round_062(monkeypatch):
    """Trigger the sanity-check branch where start_id > end_id + 1.

    Expectation: a warning is emitted and history becomes empty.
    """
    m = importlib.import_module("openhands.controller.state.state_tracker")

    # Patch the delegate classes so isinstance checks operate on our fakes
    monkeypatch.setattr(m, "AgentDelegateAction", FakeAction, raising=False)
    monkeypatch.setattr(m, "AgentDelegateObservation", FakeObservation, raising=False)

    # Capture warnings emitted to logger.warning
    warnings = []

    def fake_warn(msg):
        warnings.append(str(msg))

    monkeypatch.setattr(m, "logger", SimpleNamespace(warning=fake_warn), raising=False)

    # Instantiate StateTracker (use real constructor) and then override state
    st = m.StateTracker(sid="sid", file_store=None, user_id="uid")
    # Create a state with start_id > end_id + 1
    st.state = SimpleNamespace(start_id=10, end_id=5, history=["previous"])

    # event_stream should not be consulted for latest id in this case, but provide a minimal one
    stream = FakeEventStream([])

    # Run _init_history
    st._init_history(stream)

    # Verify branch: history emptied and warning logged
    assert st.state.history == []
    assert any("start_id" in str(w) and "greater than end_id" in str(w) for w in warnings)


def test_delegate_action_observation_pair_filtering_round_062(monkeypatch):
    """Create events with a delegate action/observation pair and verify filtering.

    Expected: events between action and observation are removed, but the action and observation
    themselves are retained, and events outside the delegate range are preserved and ordered.
    """
    m = importlib.import_module("openhands.controller.state.state_tracker")
    monkeypatch.setattr(m, "AgentDelegateAction", FakeAction, raising=False)
    monkeypatch.setattr(m, "AgentDelegateObservation", FakeObservation, raising=False)

    # Set a logger that will record calls if any (not required for this test)
    monkeypatch.setattr(m, "logger", SimpleNamespace(warning=lambda *_: None), raising=False)

    st = m.StateTracker(sid="sid", file_store=None, user_id="uid")
    # state range covers all test events
    st.state = SimpleNamespace(start_id=0, end_id=10, history=None)

    # Build events: 1 (normal), 2 (delegate action), 3 (internal), 4 (delegate observation), 5 (after)
    events = [FakeEvent(1), FakeAction(2), FakeEvent(3), FakeObservation(4), FakeEvent(5)]
    stream = FakeEventStream(events)

    # Run init
    st._init_history(stream)

    # The history should include 1,2,4,5 in that order (3 removed because it's between 2 and 4)
    got_ids = _ids(st.state.history)
    assert got_ids == [1, 2, 4, 5], f"unexpected history ids: {got_ids}"


def test_unmatched_delegate_observation_warns_round_062(monkeypatch):
    """If an AgentDelegateObservation is found without a prior action, a warning is emitted.

    The observation remains in the events list (no delegate range created), and final history
    should equal the original events returned by search_events.
    """
    m = importlib.import_module("openhands.controller.state.state_tracker")
    monkeypatch.setattr(m, "AgentDelegateAction", FakeAction, raising=False)
    monkeypatch.setattr(m, "AgentDelegateObservation", FakeObservation, raising=False)

    warnings = []

    def fake_warn(msg):
        warnings.append(str(msg))

    monkeypatch.setattr(m, "logger", SimpleNamespace(warning=fake_warn), raising=False)

    st = m.StateTracker(sid="sid", file_store=None, user_id="uid")
    st.state = SimpleNamespace(start_id=0, end_id=10, history=None)

    events = [FakeEvent(1), FakeObservation(2), FakeEvent(3)]
    stream = FakeEventStream(events)

    st._init_history(stream)

    # Ensure warning about unmatched observation was emitted
    assert any("without matching action" in w or "without matching" in w for w in warnings)

    # Because no delegate_ranges were built, history should equal the entire events list
    assert _ids(st.state.history) == [1, 2, 3]
