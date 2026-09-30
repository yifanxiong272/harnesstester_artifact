import importlib
import asyncio
import pytest
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_null_action_and_null_observation_return_round_058(monkeypatch):
    """NullAction and NullObservation should be no-ops (no send calls).

    Covers lines: 326-329 (early returns).
    """
    mod = importlib.import_module("openhands.server.session.session")

    # Create fake sentinel classes and patch them into the module
    class FakeNullAction:
        pass

    class FakeNullObservation:
        pass

    monkeypatch.setattr(mod, "NullAction", FakeNullAction)
    monkeypatch.setattr(mod, "NullObservation", FakeNullObservation)

    # Minimal WebSession instance (avoid calling real __init__)
    WebSession = mod.WebSession
    inst = object.__new__(WebSession)

    send_calls = []

    async def fake_send(data):
        send_calls.append(data)

    inst.send = fake_send
    # Provide a logger to ensure attribute exists if used later
    inst.logger = SimpleNamespace(error=lambda *a, **k: None)

    # NullAction event -> should return without calling send
    null_action = FakeNullAction()
    await inst._on_event(null_action)

    # NullObservation event -> should return without calling send
    null_obs = FakeNullObservation()
    await inst._on_event(null_obs)

    assert send_calls == [], "send should not be called for NullAction/NullObservation"


@pytest.mark.asyncio
async def test_agent_and_user_event_send_round_058(monkeypatch):
    """Events with source AGENT or USER should be converted via event_to_dict and sent as-is.

    Covers lines: 330-333 (agent/user branches).
    """
    mod = importlib.import_module("openhands.server.session.session")

    # Fake EventSource values
    EventSource = SimpleNamespace(AGENT="agent", USER="user", ENVIRONMENT="env")
    monkeypatch.setattr(mod, "EventSource", EventSource)

    # Provide a simple event_to_dict that returns identifiable dicts
    def fake_event_to_dict(event):
        return {"type": event.__class__.__name__, "payload": getattr(event, "payload", None)}

    monkeypatch.setattr(mod, "event_to_dict", fake_event_to_dict)

    # Minimal WebSession instance
    WebSession = mod.WebSession
    inst = object.__new__(WebSession)
    send_calls = []

    async def fake_send(data):
        send_calls.append(data)

    inst.send = fake_send
    inst.logger = SimpleNamespace(error=lambda *a, **k: None)

    # Create events with .source attribute
    class E1:
        def __init__(self):
            self.source = EventSource.AGENT
            self.payload = "from_agent"

    class E2:
        def __init__(self):
            self.source = EventSource.USER
            self.payload = "from_user"

    e1 = E1()
    e2 = E2()

    await inst._on_event(e1)
    await inst._on_event(e2)

    assert send_calls == [
        {"type": "E1", "payload": "from_agent"},
        {"type": "E2", "payload": "from_user"},
    ]


@pytest.mark.asyncio
async def test_environment_observations_and_agent_state_error_round_058(monkeypatch):
    """Environment observations should be re-sourced to AGENT and sent; AgentState.ERROR triggers logger.error.

    Covers lines: 335-351 (environment handling and agent state error logging).
    """
    mod = importlib.import_module("openhands.server.session.session")

    # Provide EventSource and AgentState constants compatible with the code
    EventSource = SimpleNamespace(AGENT="agent", USER="user", ENVIRONMENT="env")
    AgentState = SimpleNamespace(ERROR="error")
    monkeypatch.setattr(mod, "EventSource", EventSource)
    monkeypatch.setattr(mod, "AgentState", AgentState)

    # Create classes used in isinstance checks and patch them
    class CmdOutputObservation:
        pass

    class AgentStateChangedObservation:
        def __init__(self, agent_state=None, reason=None):
            self.agent_state = agent_state
            self.reason = reason
            self.source = EventSource.ENVIRONMENT

    class RecallObservation:
        pass

    monkeypatch.setattr(mod, "CmdOutputObservation", CmdOutputObservation)
    monkeypatch.setattr(mod, "AgentStateChangedObservation", AgentStateChangedObservation)
    monkeypatch.setattr(mod, "RecallObservation", RecallObservation)

    # event_to_dict returns a dict; we verify the handler overwrites 'source'
    def fake_event_to_dict(event):
        return {"type": event.__class__.__name__, "reason": getattr(event, "reason", None)}

    monkeypatch.setattr(mod, "event_to_dict", fake_event_to_dict)

    # Prepare WebSession instance with capturing send and logger.error
    WebSession = mod.WebSession
    inst = object.__new__(WebSession)
    send_calls = []
    logged = []

    async def fake_send(data):
        send_calls.append(data)

    def fake_logger_error(message, extra=None):
        logged.append({"message": message, "extra": extra})

    inst.send = fake_send
    inst.logger = SimpleNamespace(error=fake_logger_error)

    # Create an AgentStateChangedObservation indicating ERROR
    evt = AgentStateChangedObservation(agent_state=AgentState.ERROR, reason="bad-things")

    await inst._on_event(evt)

    # send should have been called once and its dict.source overridden to AGENT
    assert len(send_calls) == 1
    sent = send_calls[0]
    assert sent["type"] == "AgentStateChangedObservation"
    # The handler sets 'source' to EventSource.AGENT explicitly
    assert sent["source"] == EventSource.AGENT

    # logger.error should have been called with the formatted reason and signal extra
    assert len(logged) == 1
    assert logged[0]["message"] == f"Agent status error: {evt.reason}"
    assert logged[0]["extra"] == {"signal": "agent_status_error"}


@pytest.mark.asyncio
async def test_error_observation_is_sent_as_agent_event_round_058(monkeypatch):
    """ErrorObservation should be converted to an AGENT-sourced dict and sent.

    Covers lines: 351-355 (ErrorObservation branch).
    """
    mod = importlib.import_module("openhands.server.session.session")

    # Setup EventSource so we can check the 'source' forced to AGENT
    EventSource = SimpleNamespace(AGENT="agent", USER="user", ENVIRONMENT="env")
    monkeypatch.setattr(mod, "EventSource", EventSource)

    # Create and patch ErrorObservation class
    class ErrorObservation:
        def __init__(self):
            # ensure source is something that avoids earlier branches
            self.source = "other"

    monkeypatch.setattr(mod, "ErrorObservation", ErrorObservation)

    # Provide a straightforward event_to_dict
    def fake_event_to_dict(event):
        return {"type": event.__class__.__name__}

    monkeypatch.setattr(mod, "event_to_dict", fake_event_to_dict)

    WebSession = mod.WebSession
    inst = object.__new__(WebSession)
    send_calls = []

    async def fake_send(data):
        send_calls.append(data)

    inst.send = fake_send
    inst.logger = SimpleNamespace(error=lambda *a, **k: None)

    err_evt = ErrorObservation()
    await inst._on_event(err_evt)

    assert len(send_calls) == 1
    assert send_calls[0]["type"] == "ErrorObservation"
    assert send_calls[0]["source"] == EventSource.AGENT
