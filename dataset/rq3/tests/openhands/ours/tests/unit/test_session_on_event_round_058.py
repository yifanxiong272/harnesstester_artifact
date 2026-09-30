import asyncio
from types import SimpleNamespace
import importlib

import pytest

# Import the module under test
import openhands.server.session.session as session

# Helper classes used to patch the session module symbols deterministically
class DummyNullAction:
    pass

class DummyNullObservation:
    pass

class DummyCmdOutputObservation:
    def __init__(self, source=None):
        self.source = source

class DummyAgentStateChangedObservation:
    def __init__(self, source=None, agent_state=None, reason=None):
        self.source = source
        self.agent_state = agent_state
        self.reason = reason

class DummyRecallObservation:
    def __init__(self, source=None):
        self.source = source

class DummyErrorObservation:
    def __init__(self, source=None):
        self.source = source

class DummySimpleEvent:
    def __init__(self, source):
        self.source = source

class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg, **kwargs):
        # keep behavior deterministic by recording exactly the args and kwargs
        self.errors.append((msg, kwargs))

class DummySelf:
    def __init__(self):
        self.sent = []
        self.logger = DummyLogger()

    async def send(self, data):
        # mimic the awaited send used by the real WebSession
        self.sent.append(data)


def _patch_common(monkeypatch, event_to_dict_return=None):
    """Apply deterministic patches to the session module so tests do not rely on
    the real project types or external services.

    - Provide simple EventSource and AgentState objects
    - Patch the event type names to dummy classes used in isinstance checks
    - Patch event_to_dict to return a predictable dictionary
    """
    # Simple, deterministic stand-ins for enums/constants
    DummyEventSource = SimpleNamespace(AGENT="AGENT", USER="USER", ENVIRONMENT="ENV")
    DummyAgentState = SimpleNamespace(ERROR="ERROR")

    monkeypatch.setattr(session, "EventSource", DummyEventSource, raising=False)
    monkeypatch.setattr(session, "AgentState", DummyAgentState, raising=False)

    # Patch the various classes used in isinstance checks
    monkeypatch.setattr(session, "NullAction", DummyNullAction, raising=False)
    monkeypatch.setattr(session, "NullObservation", DummyNullObservation, raising=False)
    monkeypatch.setattr(session, "CmdOutputObservation", DummyCmdOutputObservation, raising=False)
    monkeypatch.setattr(session, "AgentStateChangedObservation", DummyAgentStateChangedObservation, raising=False)
    monkeypatch.setattr(session, "RecallObservation", DummyRecallObservation, raising=False)
    monkeypatch.setattr(session, "ErrorObservation", DummyErrorObservation, raising=False)

    # Patch event_to_dict to return a shallow dict we can assert on.
    if event_to_dict_return is None:
        def _event_to_dict(event):
            return {"orig_source": getattr(event, "source", None)}
    else:
        def _event_to_dict(event):
            # always return a copy of provided mapping to avoid shared mutation between tests
            return dict(event_to_dict_return)

    monkeypatch.setattr(session, "event_to_dict", _event_to_dict, raising=False)


def run_on_event(obj_self, event):
    # run the coroutine synchronously via asyncio.run for deterministic execution in pytest
    return asyncio.run(session.WebSession._on_event(obj_self, event))


def test_nulls_round_058(monkeypatch):
    """NullAction and NullObservation should cause immediate returns and not call send."""
    _patch_common(monkeypatch)

    s = DummySelf()

    # NullAction branch
    null_action = DummyNullAction()
    # ensure it is recognized by isinstance in the patched module
    run_on_event(s, null_action)
    assert s.sent == [], "NullAction must not trigger send"

    # NullObservation branch
    s2 = DummySelf()
    null_obs = DummyNullObservation()
    run_on_event(s2, null_obs)
    assert s2.sent == [], "NullObservation must not trigger send"


def test_agent_and_user_send_round_058(monkeypatch):
    """Events from AGENT and USER should be forwarded via send with event_to_dict output."""
    # Make event_to_dict return a simple predictable payload
    _patch_common(monkeypatch, event_to_dict_return={"x": 1})

    s = DummySelf()

    # AGENT source: should await send with the event_to_dict result
    agent_event = DummySimpleEvent(session.EventSource.AGENT)
    run_on_event(s, agent_event)
    assert s.sent == [{"x": 1}], "AGENT source must forward event_to_dict result unchanged"

    # USER source: should also forward
    s2 = DummySelf()
    user_event = DummySimpleEvent(session.EventSource.USER)
    run_on_event(s2, user_event)
    assert s2.sent == [{"x": 1}], "USER source must forward event_to_dict result unchanged"


def test_environment_and_agent_state_error_round_058(monkeypatch):
    """ENVIRONMENT observations from specific types should be converted to AGENT source and sent.
    Additionally, AgentStateChangedObservation with ERROR should call logger.error.
    """
    # event_to_dict returns its own dict so we can observe the 'source' mutation
    _patch_common(monkeypatch, event_to_dict_return={"payload": "ok"})

    # CmdOutputObservation path: should be converted to agent event
    s = DummySelf()
    cmd_obs = DummyCmdOutputObservation(session.EventSource.ENVIRONMENT)
    run_on_event(s, cmd_obs)
    assert len(s.sent) == 1
    sent0 = s.sent[0]
    # event_to_dict was a dict that should have been mutated to set 'source' to EventSource.AGENT
    assert sent0.get("payload") == "ok"
    assert sent0.get("source") == session.EventSource.AGENT
    # No logger error expected for CmdOutputObservation
    assert s.logger.errors == []

    # AgentStateChangedObservation which signals ERROR should log an error
    s2 = DummySelf()
    err_reason = "something failed"
    agent_state_err = DummyAgentStateChangedObservation(
        source=session.EventSource.ENVIRONMENT,
        agent_state=session.AgentState.ERROR,
        reason=err_reason,
    )
    run_on_event(s2, agent_state_err)
    assert len(s2.sent) == 1
    sent1 = s2.sent[0]
    assert sent1.get("payload") == "ok"
    assert sent1.get("source") == session.EventSource.AGENT

    # Check that logger.error was called with a message containing the reason and extra includes the signal
    assert s2.logger.errors, "Expected logger.error to be called when agent state is ERROR"
    msg, kwargs = s2.logger.errors[0]
    assert err_reason in msg
    # extra passed as keyword 'extra' in the real call; ensure 'signal' in extra mapping
    extra = kwargs.get("extra")
    assert isinstance(extra, dict) and extra.get("signal") == "agent_status_error"


def test_error_observation_round_058(monkeypatch):
    """ErrorObservation should be converted to AGENT source and sent to the UI."""
    _patch_common(monkeypatch, event_to_dict_return={"error": True})

    s = DummySelf()
    err_obs = DummyErrorObservation(source=None)
    run_on_event(s, err_obs)
    assert len(s.sent) == 1
    sent = s.sent[0]
    assert sent.get("error") is True
    assert sent.get("source") == session.EventSource.AGENT
