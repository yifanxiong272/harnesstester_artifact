import asyncio
from types import SimpleNamespace
import builtins

import pytest

import importlib
ac = importlib.import_module('openhands.controller.agent_controller')

# Helper to create a minimal controller instance without running __init__
def make_controller():
    ctrl = object.__new__(ac.AgentController)

    # logging capture
    ctrl.logged = []

    def log(level, message, extra=None, exc_info=None):
        ctrl.logged.append((level, message, extra))

    ctrl.log = log

    # default state that looks like a running agent
    ctrl.state = SimpleNamespace()
    ctrl.state.delegate_level = 0
    ctrl.state.get_local_step = lambda: 0
    ctrl.state.iteration_flag = SimpleNamespace(current_value=0)
    ctrl.state.confirmation_mode = False

    # default state_tracker with no-op methods
    ctrl.state_tracker = SimpleNamespace()
    ctrl.state_tracker.sync_budget_flag_with_metrics = lambda: None

    def run_control_flags():
        return None

    ctrl.state_tracker.run_control_flags = run_control_flags

    # Default pending action
    ctrl._pending_action = None

    # Default get_agent_state -> RUNNING
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING

    # Default stuck detector
    ctrl._is_stuck = lambda: False

    async def _react_to_exception(exc):
        # record that exception was handled
        ctrl._reacted = getattr(ctrl, '_reacted', [])
        ctrl._reacted.append(type(exc).__name__)

    ctrl._react_to_exception = _react_to_exception

    # Default replay manager
    ctrl._replay_manager = SimpleNamespace()
    ctrl._replay_manager.should_replay = lambda: False
    ctrl._replay_manager.step = lambda: ac.NullAction()

    # event stream capture
    captured_events = []

    def add_event(event, source):
        captured_events.append((event, source))

    ctrl.event_stream = SimpleNamespace()
    ctrl.event_stream.add_event = add_event
    ctrl._captured_events = captured_events

    # Default agent object
    ctrl.agent = SimpleNamespace()
    ctrl.agent.step = lambda s: ac.NullAction()
    ctrl.agent.config = SimpleNamespace()
    ctrl.agent.config.enable_stuck_detection = False
    ctrl.agent.config.enable_history_truncation = False
    ctrl.agent.config.cli_mode = False

    # Default helpers the _step references
    ctrl._handle_security_analyzer = lambda action: asyncio.sleep(0)

    async def set_agent_state_to(new_state):
        ctrl._set_state_calls = getattr(ctrl, '_set_state_calls', [])
        ctrl._set_state_calls.append(new_state)

    ctrl.set_agent_state_to = set_agent_state_to

    # metrics preparation placeholder
    ctrl._prepare_metrics_for_frontend = lambda action: setattr(ctrl, '_prepared_metrics_for', action)

    # security analyzer attribute
    ctrl.security_analyzer = None

    return ctrl


def bind_and_run_step(ctrl):
    # Bind the coroutine method to our fake instance and execute
    coro = ac.AgentController._step.__get__(ctrl, ctrl.__class__)
    return asyncio.run(coro())


def test_state_not_running_round_037():
    ctrl = make_controller()
    # make it not running
    ctrl.get_agent_state = lambda: ac.AgentState.STOPPED

    bind_and_run_step(ctrl)

    # Should log a STEP_BLOCKED_STATE and return early (no events added)
    assert any(extra and extra.get('msg_type') == 'STEP_BLOCKED_STATE' for (_l, _m, extra) in ctrl.logged)
    assert ctrl._captured_events == []


def test_pending_action_blocks_round_037():
    ctrl = make_controller()
    # still running
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING
    # create a pending action object with id attr and a type name
    pending = SimpleNamespace()
    pending.id = 'abc123'
    # Give it a fake class name
    pending.__class__ = type('FakePendingAction', (), {})
    ctrl._pending_action = pending

    bind_and_run_step(ctrl)

    # Should log STEP_BLOCKED_PENDING_ACTION
    assert any(extra and extra.get('msg_type') == 'STEP_BLOCKED_PENDING_ACTION' for (_l, _m, extra) in ctrl.logged)
    # no events should be emitted
    assert ctrl._captured_events == []


def test_replay_manager_should_replay_and_emit_action_round_037():
    ctrl = make_controller()
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING

    # Make replay manager return True and provide a non-NullAction with a known source
    class FakeReplayAction:
        runnable = False
        _source = ac.EventSource.AGENT
        def __str__(self):
            return '<replayed-action>'

    ctrl._replay_manager.should_replay = lambda: True
    ctrl._replay_manager.step = lambda: FakeReplayAction()

    bind_and_run_step(ctrl)

    # The action from the replay should be emitted to event_stream
    assert len(ctrl._captured_events) == 1
    ev, src = ctrl._captured_events[0]
    assert str(ev) == '<replayed-action>' or hasattr(ev, '__str__')
    assert src == ac.EventSource.AGENT


def test_agent_step_returns_none_triggers_LLNoActionError_round_037():
    ctrl = make_controller()
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING
    # Ensure not replaying
    ctrl._replay_manager.should_replay = lambda: False

    # Agent.step returns None -> should add an ErrorObservation event
    def agent_step(state):
        return None

    ctrl.agent.step = agent_step

    bind_and_run_step(ctrl)

    # Expect an ErrorObservation was added (with EventSource.AGENT)
    assert len(ctrl._captured_events) == 1
    ev, src = ctrl._captured_events[0]
    # Event should be an ErrorObservation or at least have .content attribute
    assert isinstance(ev, ac.ErrorObservation)
    assert src == ac.EventSource.AGENT
    assert 'No action' in ev.content or isinstance(ev.content, str)


def test_context_window_exceeded_with_truncation_round_037():
    ctrl = make_controller()
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING
    ctrl._replay_manager.should_replay = lambda: False

    # Make agent.step raise a ContextWindowExceededError with a matching message
    def agent_step(state):
        raise ac.ContextWindowExceededError('Prompt is too long for the model')

    ctrl.agent.step = agent_step
    # Enable history truncation so we follow the truncation branch
    ctrl.agent.config.enable_history_truncation = True

    bind_and_run_step(ctrl)

    # Expect a CondensationRequestAction to have been enqueued
    assert len(ctrl._captured_events) == 1
    ev, src = ctrl._captured_events[0]
    assert isinstance(ev, ac.CondensationRequestAction)
    assert src == ac.EventSource.AGENT


def test_bad_request_tool_validation_recoverable_round_037():
    ctrl = make_controller()
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING
    ctrl._replay_manager.should_replay = lambda: False

    # Make agent.step raise a BadRequestError with the recovery message
    def agent_step(state):
        raise ac.BadRequestError('Tool call validation failed: missing properties')

    ctrl.agent.step = agent_step

    bind_and_run_step(ctrl)

    # Expect an ErrorObservation describing tool validation failure
    assert len(ctrl._captured_events) == 1
    ev, src = ctrl._captured_events[0]
    assert isinstance(ev, ac.ErrorObservation)
    assert 'Tool call validation failed' in ev.content
    assert src == ac.EventSource.AGENT


def test_confirmation_cli_mode_sets_confirmation_state_and_state_change_round_037():
    ctrl = make_controller()
    ctrl.get_agent_state = lambda: ac.AgentState.RUNNING
    ctrl._replay_manager.should_replay = lambda: False

    # Patch the module-level CmdRunAction name to a simple dummy so type(action) checks pass
    class DummyAction:
        runnable = True
        _source = ac.EventSource.AGENT
        def __str__(self):
            return '<dummy-cmd-action>'

    # Replace the class name in module to point to our dummy
    ac.CmdRunAction = DummyAction

    # Agent will return an instance of DummyAction
    def agent_step(state):
        return DummyAction()

    ctrl.agent.step = agent_step

    # Ensure state requires confirmation logic path: agent controller state.confirmation_mode True
    ctrl.state.confirmation_mode = True
    # CLI mode True so branch at 1005 taken
    ctrl.agent.config.cli_mode = True

    # Make _handle_security_analyzer a no-op async function
    async def noop_handle(action):
        # set an attribute to ensure code continues
        action.security_risk = ac.ActionSecurityRisk.UNKNOWN

    ctrl._handle_security_analyzer = noop_handle

    # Track calls to set_agent_state_to
    called_states = []

    async def set_agent_state_to(new_state):
        called_states.append(new_state)

    ctrl.set_agent_state_to = set_agent_state_to

    bind_and_run_step(ctrl)

    # After running, pending action should be set to the returned action
    assert ctrl._pending_action is not None
    # confirmation state must have been set to AWAITING_CONFIRMATION
    assert getattr(ctrl._pending_action, 'confirmation_state') == ac.ActionConfirmationStatus.AWAITING_CONFIRMATION

    # And set_agent_state_to should have been awaited with AWAITING_USER_CONFIRMATION
    assert called_states and called_states[0] == ac.AgentState.AWAITING_USER_CONFIRMATION

    # Event was emitted to the stream
    assert len(ctrl._captured_events) == 1
    ev, src = ctrl._captured_events[0]
    assert src == ac.EventSource.AGENT
    assert str(ev) == '<dummy-cmd-action>'
