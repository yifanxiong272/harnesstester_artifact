import pytest
import types

import importlib

session_mod = importlib.import_module('openhands.server.session.session')

class DummySelf:
    def __init__(self):
        self.sent = []
        self.logger = types.SimpleNamespace(error=lambda *a, **k: self._record_error(a, k))
        self._errors = []

    async def send(self, data):
        # record a shallow copy to avoid mutation issues
        self.sent.append(dict(data))

    def _record_error(self, args, kwargs):
        self._errors.append((args, kwargs))


@pytest.mark.asyncio
async def test_null_action_and_null_observation_round_058(monkeypatch):
    """Ensure NullAction and NullObservation are ignored (no send)."""
    # Create dummy marker classes and patch them into the module
    class DummyNullAction:
        pass

    class DummyNullObservation:
        pass

    monkeypatch.setattr(session_mod, 'NullAction', DummyNullAction)
    monkeypatch.setattr(session_mod, 'NullObservation', DummyNullObservation)

    dummy = DummySelf()

    # Create instances of the dummy classes
    na = DummyNullAction()
    no = DummyNullObservation()

    # Call the async handler for each and assert send not called
    await session_mod.WebSession._on_event(dummy, na)
    await session_mod.WebSession._on_event(dummy, no)

    assert dummy.sent == [], "send should not be called for NullAction/NullObservation"


@pytest.mark.asyncio
async def test_agent_and_user_source_round_058(monkeypatch):
    """When event.source is AGENT or USER, the event dict from event_to_dict is sent as-is."""
    # Minimal EventSource replacement
    class ES:
        AGENT = 'agent'
        USER = 'user'
        ENVIRONMENT = 'environment'

    # Patch EventSource and event_to_dict
    monkeypatch.setattr(session_mod, 'EventSource', ES)

    def fake_event_to_dict(ev):
        # produce a dict unique per instance (use attribute if present)
        return {'sent_for': getattr(ev, 'name', ev.__class__.__name__)}

    monkeypatch.setattr(session_mod, 'event_to_dict', fake_event_to_dict)

    # Create simple event objects with .source
    class Ev:
        def __init__(self, source, name):
            self.source = source
            self.name = name

    dummy = DummySelf()

    ev_agent = Ev(ES.AGENT, 'A')
    ev_user = Ev(ES.USER, 'U')

    await session_mod.WebSession._on_event(dummy, ev_agent)
    await session_mod.WebSession._on_event(dummy, ev_user)

    # Two sends should have occurred with the dict returned by fake_event_to_dict
    assert len(dummy.sent) == 2
    assert dummy.sent[0] == {'sent_for': 'A'}
    assert dummy.sent[1] == {'sent_for': 'U'}


@pytest.mark.asyncio
async def test_environment_observations_and_error_round_058(monkeypatch):
    """Cover ENVIRONMENT observation handling, AgentState.ERROR logging, and ErrorObservation sending.

    - ENVIRONMENT + CmdOutputObservation -> send with source changed to AGENT
    - ENVIRONMENT + AgentStateChangedObservation with AgentState.ERROR -> logger.error called
    - ErrorObservation -> send with source changed to AGENT
    """
    # Replace EventSource and AgentState with simple sentinels
    class ES:
        AGENT = 'agent'
        USER = 'user'
        ENVIRONMENT = 'environment'

    class AS:
        ERROR = 'error'
        OK = 'ok'

    monkeypatch.setattr(session_mod, 'EventSource', ES)
    monkeypatch.setattr(session_mod, 'AgentState', AS)

    # Create dummy observation classes and patch them in
    class CmdOutputObservation:
        pass

    class AgentStateChangedObservation:
        def __init__(self, agent_state=None, reason=None):
            self.agent_state = agent_state
            self.reason = reason

    class RecallObservation:
        pass

    class ErrorObservation:
        pass

    monkeypatch.setattr(session_mod, 'CmdOutputObservation', CmdOutputObservation)
    monkeypatch.setattr(session_mod, 'AgentStateChangedObservation', AgentStateChangedObservation)
    monkeypatch.setattr(session_mod, 'RecallObservation', RecallObservation)
    monkeypatch.setattr(session_mod, 'ErrorObservation', ErrorObservation)

    # event_to_dict should return a dict that may or may not have 'source'
    def fake_event_to_dict(ev):
        # include identifying info to assert mutated source
        base = {'type': ev.__class__.__name__}
        # include reason if present
        if hasattr(ev, 'reason') and ev.reason is not None:
            base['reason'] = ev.reason
        return base

    monkeypatch.setattr(session_mod, 'event_to_dict', fake_event_to_dict)

    dummy = DummySelf()

    # 1) ENVIRONMENT + CmdOutputObservation
    cmd_ev = CmdOutputObservation()
    cmd_ev.source = ES.ENVIRONMENT

    await session_mod.WebSession._on_event(dummy, cmd_ev)

    # the event_to_dict result should have been sent, with source overwritten to AGENT
    assert any(sent.get('type') == 'CmdOutputObservation' and sent.get('source') == ES.AGENT for sent in dummy.sent)

    # 2) ENVIRONMENT + AgentStateChangedObservation with ERROR should log an error
    err_ev = AgentStateChangedObservation(agent_state=AS.ERROR, reason='bang')
    err_ev.source = ES.ENVIRONMENT

    prev_error_count = len(dummy._errors)
    await session_mod.WebSession._on_event(dummy, err_ev)

    # event should be sent with source overwritten and logger.error should have been called once
    assert any(sent.get('type') == 'AgentStateChangedObservation' and sent.get('source') == ES.AGENT for sent in dummy.sent)
    assert len(dummy._errors) >= prev_error_count + 1, "logger.error should be called for AgentState.ERROR"

    # 3) ErrorObservation instance triggers its own branch and is sent as AGENT
    err_obs = ErrorObservation()
    # Provide a .source attribute so earlier unconditional access does not raise; choose a value
    # that avoids matching AGENT/USER/ENVIRONMENT to reach the isinstance(ErrorObservation) branch.
    err_obs.source = 'external'

    await session_mod.WebSession._on_event(dummy, err_obs)

    assert any(sent.get('type') == 'ErrorObservation' and sent.get('source') == ES.AGENT for sent in dummy.sent)
