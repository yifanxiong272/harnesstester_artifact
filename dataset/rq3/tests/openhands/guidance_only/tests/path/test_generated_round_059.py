import types
import builtins
import pytest

from openhands.controller import agent_controller as ac

# Deterministic, minimal fakes to exercise AgentController.end_delegate
class FakeLoop:
    def __init__(self):
        self.recorded = None

    def run_until_complete(self, coro):
        # record exactly what was passed in for later assertions
        self.recorded = coro
        return None

class IterFlag:
    def __init__(self, v=None):
        self.current_value = v

class FakeStateObj:
    def __init__(self, outputs=None, iter_val=None):
        self.outputs = {} if outputs is None else outputs
        self.iteration_flag = IterFlag(iter_val)

class FakeObservation:
    def __init__(self, outputs, content):
        self.outputs = outputs
        self.content = content
        # set default for tool metadata (may be patched by end_delegate)
        self.tool_call_metadata = None

class FakeAgentDelegateAction:
    def __init__(self, tool_call_metadata=None):
        self.tool_call_metadata = tool_call_metadata

class FakeEventStream:
    def __init__(self):
        self.added = []

    def add_event(self, obs, source):
        self.added.append((obs, source))

class FakeControllerState:
    def __init__(self, history=None, iter_val=0):
        self.iteration_flag = IterFlag(iter_val)
        self._metrics = {"local": 1}
        self.history = [] if history is None else history

    def get_local_metrics(self):
        return dict(self._metrics)

class DummyAgent:
    def __init__(self, name):
        self.name = name

class FakeDelegate:
    def __init__(self, state_obj, agent_name, close_return_value="closed"):
        self.state = state_obj
        self.agent = DummyAgent(agent_name)
        # close is expected to be called and its return passed to run_until_complete
        self._close_return = close_return_value

    def get_agent_state(self):
        # This will be patched per-test to return appropriate AgentState value
        # but keep a fallback if tests decide to use state flag directly
        return getattr(self, "_agent_state_value", None)

    def close(self):
        # emulate being called (synchronous object returned) so fake loop records it
        return self._close_return


def _prepare_controller():
    # Create an AgentController instance without invoking full __init__
    controller = object.__new__(ac.AgentController)
    return controller


def test_end_delegate_finished_with_tool_metadata_round_059(monkeypatch):
    """Path: delegate present + FINISHED state + AgentDelegateAction in history

    Asserts:
    - iteration_flag propagated from delegate.state
    - delegate.close() passed to asyncio event loop
    - AgentDelegateObservation was emitted with outputs filtered (no 'metrics')
    - tool_call_metadata copied from AgentDelegateAction
    - controller.delegate unset at end
    """
    # Patch module-level symbols to deterministic fakes
    monkeypatch.setattr(ac, "AgentDelegateObservation", FakeObservation)
    monkeypatch.setattr(ac, "AgentDelegateAction", FakeAgentDelegateAction)
    # Provide a simple EventSource with AGENT sentinel
    monkeypatch.setattr(ac, "EventSource", types.SimpleNamespace(AGENT="agent"))

    # Replace AgentState with a simple namespace for control
    FakeAgentState = types.SimpleNamespace(FINISHED="FIN", REJECTED="REJ", ERROR="ERR")
    monkeypatch.setattr(ac, "AgentState", FakeAgentState)

    # Patch asyncio.get_event_loop to return our FakeLoop instance
    fake_loop = FakeLoop()
    monkeypatch.setattr(ac.asyncio, "get_event_loop", lambda: fake_loop)

    # Build delegate with outputs including a 'metrics' key which should be filtered
    delegate_state = FakeStateObj(outputs={"result": "ok", "metrics": {"m": 1}}, iter_val=42)
    delegate = FakeDelegate(delegate_state, agent_name="delegator", close_return_value="closed-call")
    delegate._agent_state_value = FakeAgentState.FINISHED

    # Controller state initially has iteration_flag value different from delegate
    initiating_action = FakeAgentDelegateAction(tool_call_metadata={"tool": "x"})
    ctrl_state = FakeControllerState(history=[initiating_action], iter_val=0)

    controller = _prepare_controller()
    controller.delegate = delegate
    controller.state = ctrl_state
    controller.event_stream = FakeEventStream()

    # execute
    controller.end_delegate()

    # Assertions
    # run_until_complete should have been called with whatever delegate.close() returned
    assert fake_loop.recorded == "closed-call"

    # iteration flag should be copied from delegate.state
    assert controller.state.iteration_flag.current_value == 42

    # One event should be emitted to the event stream
    assert len(controller.event_stream.added) == 1
    obs, source = controller.event_stream.added[0]
    assert source == "agent"

    # Observation outputs should reference the delegate outputs (original dict)
    assert obs.outputs == {"result": "ok", "metrics": {"m": 1}}

    # The textual content should mention that the delegator 'finishes task' and include the result
    assert "delegator finishes task" in obs.content
    assert "result: ok" in obs.content

    # tool_call_metadata should have been copied from the AgentDelegateAction in history
    assert obs.tool_call_metadata == {"tool": "x"}

    # controller.delegate should have been unset
    assert controller.delegate is None


def test_end_delegate_error_without_tool_metadata_round_059(monkeypatch):
    """Path: delegate present + ERROR state + no AgentDelegateAction in history

    Asserts:
    - error content path used
    - no tool_call_metadata set on observation
    - controller.delegate unset at end
    """
    # Patch observation and event source again
    monkeypatch.setattr(ac, "AgentDelegateObservation", FakeObservation)
    # Ensure AgentDelegateAction type exists but will not be present in history
    monkeypatch.setattr(ac, "AgentDelegateAction", FakeAgentDelegateAction)
    monkeypatch.setattr(ac, "EventSource", types.SimpleNamespace(AGENT="agent"))

    FakeAgentState = types.SimpleNamespace(FINISHED="FIN", REJECTED="REJ", ERROR="ERR")
    monkeypatch.setattr(ac, "AgentState", FakeAgentState)

    # Patch asyncio loop
    fake_loop = FakeLoop()
    monkeypatch.setattr(ac.asyncio, "get_event_loop", lambda: fake_loop)

    # Build a delegate in ERROR state. Provide no 'metrics' and a minimal outputs dict
    delegate_state = FakeStateObj(outputs={"error_code": 123}, iter_val=7)
    delegate = FakeDelegate(delegate_state, agent_name="errbot", close_return_value="closed2")
    delegate._agent_state_value = FakeAgentState.ERROR

    # Controller history contains events but none of them are AgentDelegateAction
    ctrl_state = FakeControllerState(history=[object()], iter_val=0)

    controller = _prepare_controller()
    controller.delegate = delegate
    controller.state = ctrl_state
    controller.event_stream = FakeEventStream()

    # execute
    controller.end_delegate()

    # run_until_complete should have been called
    assert fake_loop.recorded == "closed2"

    # iteration flag should be copied from delegate.state
    assert controller.state.iteration_flag.current_value == 7

    # One event should be emitted
    assert len(controller.event_stream.added) == 1
    obs, source = controller.event_stream.added[0]
    assert source == "agent"

    # Error content branch should be used
    assert "encountered an error" in obs.content

    # No tool_call_metadata should have been assigned since no AgentDelegateAction in history
    assert obs.tool_call_metadata is None

    # controller.delegate should have been unset
    assert controller.delegate is None
