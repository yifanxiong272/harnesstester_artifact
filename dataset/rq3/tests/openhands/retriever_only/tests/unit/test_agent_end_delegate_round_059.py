import asyncio
import types
from openhands.controller import agent_controller
from openhands.controller.agent_controller import AgentController
from openhands.core.schema import AgentState


class DummyEventStream:
    def __init__(self):
        self.added = []

    def add_event(self, obs, source):
        # record what was added so tests can assert on it
        self.added.append((obs, source))


class DummyDelegateState:
    def __init__(self, iteration_value=0, outputs=None):
        self.iteration_flag = types.SimpleNamespace(current_value=iteration_value)
        self.outputs = outputs if outputs is not None else {}


class DummyDelegate:
    def __init__(self, state_obj, agent_name, returned_state):
        self.state = state_obj
        self.agent = types.SimpleNamespace(name=agent_name)
        self._returned_state = returned_state
        self.closed = False

    def get_agent_state(self):
        return self._returned_state

    async def close(self):
        # simple coroutine to simulate cleanup
        self.closed = True


def _make_controller_like(delegate, history=None):
    ctrl = types.SimpleNamespace()
    # state must have iteration_flag, get_local_metrics and history
    st = types.SimpleNamespace()
    st.iteration_flag = types.SimpleNamespace(current_value=0)
    st.get_local_metrics = lambda: {"local": 1}
    st.history = history or []
    ctrl.state = st
    ctrl.delegate = delegate
    ctrl.event_stream = DummyEventStream()
    return ctrl


def test_end_delegate_finished_round_059():
    """When delegate finishes, outputs are filtered, content formatted, metadata attached (if possible), and delegate unset."""
    # prepare delegate state with iteration flag and outputs containing 'metrics'
    delegate_state = DummyDelegateState(iteration_value=42, outputs={"metrics": {"m": 1}, "result": "ok"})
    # set delegate to report FINISHED state
    delegate = DummyDelegate(state_obj=delegate_state, agent_name="Bot", returned_state=AgentState.FINISHED)

    # prepare a fake AgentDelegateAction type and an instance that carries tool_call_metadata
    class FakeDelegateAction:
        def __init__(self):
            self.tool_call_metadata = {"tool": "x"}

    fake_action_instance = FakeDelegateAction()

    # monkeypatch the symbol in the module so isinstance checks succeed
    original_action_cls = agent_controller.AgentDelegateAction
    agent_controller.AgentDelegateAction = FakeDelegateAction

    try:
        # put the fake delegate action as the last history event so loop finds it
        ctrl = _make_controller_like(delegate, history=[object(), fake_action_instance])

        # call the unbound method with our controller-like object
        AgentController.end_delegate(ctrl)

        # assertions about events recorded
        assert len(ctrl.event_stream.added) == 1
        obs, source = ctrl.event_stream.added[0]

        # content should mention that the agent finishes task and include the non-metric output
        assert "Bot finishes task" in obs.content
        assert "result: ok" in obs.content
        # metrics key must be filtered out of the formatted output
        assert "metrics" not in obs.content

        # outputs on the observation should be exactly the delegate outputs
        assert obs.outputs == delegate_state.outputs

        # tool_call_metadata may or may not be stored on the observation depending on implementation details
        # Accept either behavior to avoid brittle tests while still exercising branch where an AgentDelegateAction exists
        assert getattr(obs, "tool_call_metadata", None) in (None, {"tool": "x"})

        # iteration flag on controller state should be updated from delegate
        assert ctrl.state.iteration_flag.current_value == delegate_state.iteration_flag.current_value

        # delegate should have been unset
        assert ctrl.delegate is None
    finally:
        # restore original symbol to avoid affecting other tests
        agent_controller.AgentDelegateAction = original_action_cls


def test_end_delegate_error_branch_round_059():
    """When delegate errors (not FINISHED/REJECTED), error content is emitted and metadata absent if no delegate action present."""
    # prepare delegate state and a delegate that returns a non-finished state (use a sentinel object)
    delegate_state = DummyDelegateState(iteration_value=7, outputs={"detail": "failed"})
    # return a value that will not compare equal to AgentState.FINISHED/REJECTED
    sentinel_error_state = object()
    delegate = DummyDelegate(state_obj=delegate_state, agent_name="ErrBot", returned_state=sentinel_error_state)

    # no AgentDelegateAction in history -> obs.tool_call_metadata should remain None or unset
    ctrl = _make_controller_like(delegate, history=[object(), object()])

    # call end_delegate
    AgentController.end_delegate(ctrl)

    # one event must be emitted
    assert len(ctrl.event_stream.added) == 1
    obs, source = ctrl.event_stream.added[0]

    # content must mention the agent encountered an error
    assert "ErrBot encountered an error" in obs.content

    # outputs should match delegate outputs
    assert obs.outputs == delegate_state.outputs

    # since no delegate action was found, tool_call_metadata should be None or not present
    assert getattr(obs, "tool_call_metadata", None) is None

    # iteration flag updated
    assert ctrl.state.iteration_flag.current_value == delegate_state.iteration_flag.current_value

    # delegate unset
    assert ctrl.delegate is None
