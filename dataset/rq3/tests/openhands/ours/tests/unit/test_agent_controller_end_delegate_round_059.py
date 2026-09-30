import types
import asyncio
import openhands.controller.agent_controller as ac
from openhands.controller.agent_controller import AgentController


# Patching module-level collaborators used by end_delegate to simple fakes
class FakeObservation:
    def __init__(self, outputs=None, content=""):
        # preserve shape: attributes used later in code
        self.outputs = outputs
        self.content = content
        # optional metadata that may be set by end_delegate
        self.tool_call_metadata = None


class FakeEventStream:
    def __init__(self):
        self.events = []

    def add_event(self, obs, source):
        # preserve call shape
        self.events.append((obs, source))


class FakeDelegateAction:
    def __init__(self, tool_call_metadata=None):
        self.tool_call_metadata = tool_call_metadata


class FakeLoop:
    def run_until_complete(self, coro):
        # run the coroutine in a fresh loop to avoid interacting with pytest's event loop
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# Apply patches to the module under test so that end_delegate will resolve these names to our fakes
ac.AgentDelegateObservation = FakeObservation
ac.AgentDelegateAction = FakeDelegateAction
ac.asyncio.get_event_loop = lambda: FakeLoop()
# silence logger calls (preserve call signature)
ac.logger.info = lambda *a, **k: None


def make_controller_with(delegate, history=None, iteration_value=None):
    """Return a plain object suitable as `self` for calling AgentController.end_delegate."""
    state = types.SimpleNamespace()
    # iteration_flag with current_value
    iter_flag = types.SimpleNamespace()
    iter_flag.current_value = iteration_value
    state.iteration_flag = iter_flag

    # get_local_metrics returns a dict (shape preserved)
    state.get_local_metrics = lambda: {"m": 1}

    # history used by end_delegate to find AgentDelegateAction instances
    state.history = history or []

    # Prepare controller namespace
    controller = types.SimpleNamespace()
    controller.state = state
    controller.event_stream = FakeEventStream()
    controller.delegate = delegate
    return controller


class DummyDelegateState:
    def __init__(self, outputs=None, iteration_value=None):
        self.outputs = outputs
        self.iteration_flag = types.SimpleNamespace(current_value=iteration_value)


class DummyAgentDescriptor:
    def __init__(self, name):
        self.name = name


class DummyDelegate:
    def __init__(self, state=None, agent_name="fake-agent", agent_state_getter=None):
        # state can be None or DummyDelegateState
        self.state = state
        self.agent = DummyAgentDescriptor(agent_name)
        # agent_state_getter returns an AgentState value when called
        self._getter = agent_state_getter

    def get_agent_state(self):
        return self._getter()

    async def close(self):
        # emulate async cleanup
        # no-op, but ensure it's an awaitable
        return None


def test_end_delegate_returns_early_when_no_delegate_round_059():
    # Case: delegate is None -> function returns immediately (lines 801->802)
    controller = make_controller_with(delegate=None)

    # Call unbound method with our controller namespace
    AgentController.end_delegate(controller)

    # ensure delegate still None and no events emitted
    assert controller.delegate is None
    assert controller.event_stream.events == []


def test_end_delegate_finished_with_metadata_round_059():
    # Case: delegate finished (AgentState.FINISHED) and history includes AgentDelegateAction
    # Prepare delegate state outputs containing a 'metrics' key which should be filtered out
    outputs = {"result": "ok", "metrics": {"score": 0.9}}
    delegate_state = DummyDelegateState(outputs=outputs, iteration_value=42)

    # agent state getter returns AgentState.FINISHED
    agent_state_getter = lambda: ac.AgentState.FINISHED
    delegate = DummyDelegate(state=delegate_state, agent_name="delegateX", agent_state_getter=agent_state_getter)

    # History contains a Fake AgentDelegateAction with tool_call_metadata
    action = FakeDelegateAction(tool_call_metadata={"call": "meta"})
    history = [object(), action]

    # Controller state iteration flag initial value different from delegate's
    controller = make_controller_with(delegate=delegate, history=history, iteration_value=0)

    # run end_delegate
    AgentController.end_delegate(controller)

    # After execution, controller.delegate should be unset
    assert controller.delegate is None

    # Exactly one event should have been emitted
    assert len(controller.event_stream.events) == 1
    obs, source = controller.event_stream.events[0]

    # The observation should be our FakeObservation with outputs equal to delegate.state.outputs
    assert isinstance(obs, FakeObservation)
    assert obs.outputs == outputs

    # The content should include the agent name and the filtered result but not the 'metrics' key
    assert "delegateX" in obs.content
    assert "result: ok" in obs.content
    assert "metrics" not in obs.content

    # The tool_call_metadata should be copied from the AgentDelegateAction in history
    assert obs.tool_call_metadata == {"call": "meta"}

    # The controller state iteration flag should have been updated from the delegate's state
    assert controller.state.iteration_flag.current_value == delegate_state.iteration_flag.current_value


def test_end_delegate_error_without_metadata_round_059():
    # Case: delegate encountered ERROR and no AgentDelegateAction present in history
    outputs = {"error_info": "bad"}
    delegate_state = DummyDelegateState(outputs=outputs, iteration_value=7)

    agent_state_getter = lambda: ac.AgentState.ERROR
    delegate = DummyDelegate(state=delegate_state, agent_name="err-agent", agent_state_getter=agent_state_getter)

    # History without any AgentDelegateAction instances
    history = [object(), object()]
    controller = make_controller_with(delegate=delegate, history=history, iteration_value=0)

    AgentController.end_delegate(controller)

    # Delegate should be unset
    assert controller.delegate is None

    # One event emitted
    assert len(controller.event_stream.events) == 1
    obs, _ = controller.event_stream.events[0]

    # Observation content should indicate an error and include the agent name
    assert "err-agent encountered an error" in obs.content

    # Since no AgentDelegateAction was present, tool_call_metadata should be None
    assert getattr(obs, "tool_call_metadata") is None
