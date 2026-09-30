# file: openhands/server/listen_socket.py:43-148
# asked: {"lines": [45, 46, 47, 48, 49, 50, 51, 52, 53, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 67, 68, 69, 71, 72, 74, 77, 78, 79, 80, 82, 83, 86, 87, 88, 90, 91, 92, 94, 96, 97, 99, 102, 105, 106, 108, 109, 110, 112, 113, 114, 116, 119, 120, 121, 124, 125, 128, 129, 132, 133, 134, 135, 136, 139, 140, 142, 143, 145, 147, 148], "branches": [[62, 63], [62, 64], [67, 68], [67, 71], [71, 72], [71, 74], [105, 106], [105, 119], [108, 112], [108, 113], [113, 114], [113, 116], [119, 120], [119, 124], [139, 140], [139, 142]]}
# gained: {"lines": [45, 46, 47, 48, 49, 50, 51, 52, 53, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 67, 68, 69, 71, 72, 74, 77, 78, 79, 80, 82, 83, 86, 87, 88, 90, 91, 92, 94, 96, 97, 99, 102, 105, 106, 108, 109, 110, 112, 113, 114, 116, 119, 120, 121, 124, 125, 128, 129, 132, 133, 134, 135, 136, 139, 140, 142, 143, 145, 147, 148], "branches": [[62, 63], [62, 64], [67, 68], [67, 71], [71, 72], [71, 74], [105, 106], [105, 119], [108, 112], [108, 113], [113, 114], [113, 116], [119, 120], [119, 124], [139, 140], [139, 142]]}

import asyncio
import inspect
import pytest
import importlib

MODULE = importlib.import_module("openhands.server.listen_socket")


@pytest.mark.asyncio
async def test_invalid_latest_event_id_and_missing_conversation(monkeypatch):
    called = {}

    # Ensure latest_event_id ValueError path is taken by providing a bad value
    environ = {"QUERY_STRING": "latest_event_id=notanint"}

    # Fake create_task to capture the coroutine passed to it
    created_tasks = []

    async def fake_disconnect(conn_id):
        called['disconnected_with'] = conn_id

    def fake_create_task(coro):
        created_tasks.append(coro)
        return "task-placeholder"

    monkeypatch.setattr(MODULE, "_invalid_session_api_key", lambda qp: False)
    # Ensure sio.disconnect exists and is coroutine
    monkeypatch.setattr(MODULE, "sio", type("SIO", (), {"disconnect": fake_disconnect, "event": MODULE.sio.event}))
    monkeypatch.setattr(MODULE.asyncio, "create_task", fake_create_task)

    with pytest.raises(MODULE.ConnectionRefusedError):
        await MODULE.connect("conn-123", environ)

    # create_task should have been called with a coroutine (disconnect coroutine)
    assert len(created_tasks) == 1
    assert inspect.iscoroutine(created_tasks[0])


@pytest.mark.asyncio
async def test_invalid_session_api_key_causes_refusal(monkeypatch):
    environ = {"QUERY_STRING": "conversation_id=convX"}

    created_tasks = []

    async def fake_disconnect(conn_id):
        created_tasks.append(("disconnected", conn_id))

    def fake_create_task(coro):
        created_tasks.append(("create_task_called", coro))
        return "task-placeholder"

    # Force invalid session API key
    monkeypatch.setattr(MODULE, "_invalid_session_api_key", lambda qp: True)

    monkeypatch.setattr(MODULE, "sio", type("SIO", (), {"disconnect": fake_disconnect, "event": MODULE.sio.event}))
    monkeypatch.setattr(MODULE.asyncio, "create_task", fake_create_task)

    with pytest.raises(MODULE.ConnectionRefusedError):
        await MODULE.connect("conn-abc", environ)

    # create_task should have been invoked to schedule sio.disconnect
    assert any(entry[0] == "create_task_called" for entry in created_tasks)


@pytest.mark.asyncio
async def test_event_store_file_not_found(monkeypatch):
    environ = {"QUERY_STRING": "conversation_id=convY"}

    created_tasks = []

    async def fake_disconnect(conn_id):
        created_tasks.append(conn_id)

    def fake_create_task(coro):
        created_tasks.append("task")
        return "task-placeholder"

    # Valid session - create_conversation_validator returns an object with method validate(self,...)
    class Validator:
        async def validate(self, conversation_id, cookies_str, authorization_header):
            return "userZ"

    monkeypatch.setattr(MODULE, "_invalid_session_api_key", lambda qp: False)
    monkeypatch.setattr(MODULE, "create_conversation_validator", lambda: Validator())
    # EventStore raises FileNotFoundError when instantiated
    class FakeEventStore:
        def __init__(self, *args, **kwargs):
            raise FileNotFoundError("no file")
    monkeypatch.setattr(MODULE, "EventStore", FakeEventStore)

    monkeypatch.setattr(MODULE, "sio", type("SIO", (), {"disconnect": fake_disconnect, "event": MODULE.sio.event, "emit": lambda *a, **k: None}))
    monkeypatch.setattr(MODULE.asyncio, "create_task", fake_create_task)

    with pytest.raises(MODULE.ConnectionRefusedError):
        await MODULE.connect("conn-file", environ)

    assert "task" in created_tasks


@pytest.mark.asyncio
async def test_replay_events_emits_and_join_success(monkeypatch):
    # Setup environment with conversation_id and providers_set
    environ = {"QUERY_STRING": "conversation_id=convGood&providers_set=p1,p2"}

    # Replace ProviderType to identity for simplicity
    monkeypatch.setattr(MODULE, "ProviderType", lambda p: p)

    # Set invalid session check to False
    monkeypatch.setattr(MODULE, "_invalid_session_api_key", lambda qp: False)

    # Fake validator that returns a user id (method)
    class Validator:
        async def validate(self, conversation_id, cookies_str, authorization_header):
            return "user_ok"

    monkeypatch.setattr(MODULE, "create_conversation_validator", lambda: Validator())

    # Prepare dummy event classes to control isinstance checks
    NullAction = type("NullAction", (), {})
    NullObservation = type("NullObservation", (), {})
    RecallAction = type("RecallAction", (), {})
    AgentStateChangedObservation = type("AgentStateChangedObservation", (), {})
    monkeypatch.setattr(MODULE, "NullAction", NullAction)
    monkeypatch.setattr(MODULE, "NullObservation", NullObservation)
    monkeypatch.setattr(MODULE, "RecallAction", RecallAction)
    monkeypatch.setattr(MODULE, "AgentStateChangedObservation", AgentStateChangedObservation)

    # Create fake events: one NullAction (skipped), one normal event (emitted), one AgentStateChangedObservation (emitted last)
    class NormalEvent:
        pass

    events = [NullAction(), NormalEvent(), AgentStateChangedObservation()]

    # Fake AsyncEventStoreWrapper to iterate over events asynchronously
    class FakeAsyncIter:
        def __init__(self, event_store, start):
            self._events = list(events)
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._events):
                raise StopAsyncIteration
            ev = self._events[self._idx]
            self._idx += 1
            return ev

    monkeypatch.setattr(MODULE, "AsyncEventStoreWrapper", FakeAsyncIter)

    # event_to_dict returns the class name
    monkeypatch.setattr(MODULE, "event_to_dict", lambda ev: {"cls": ev.__class__.__name__})

    # Capture emits
    emit_calls = []

    async def fake_emit(name, data, to=None):
        emit_calls.append((name, data, to))

    # conversation_manager join_conversation returns a truthy value
    async def fake_join_conversation(conversation_id, connection_id, init_data, user_id):
        return {"ok": True}

    # setup_init_conversation_settings returns empty dict
    async def fake_setup_init_conversation_settings(user_id, conversation_id, providers_set):
        return {"init": True}

    # Fake sio with emit and disconnect
    monkeypatch.setattr(MODULE, "sio", type("SIO", (), {"emit": fake_emit, "disconnect": lambda conn: None, "event": MODULE.sio.event}))

    monkeypatch.setattr(MODULE.conversation_manager, "join_conversation", fake_join_conversation)
    monkeypatch.setattr(MODULE, "setup_init_conversation_settings", fake_setup_init_conversation_settings)

    # Run connect
    await MODULE.connect("connection-good", environ)

    # Should have emitted 2 events: NormalEvent then AgentStateChangedObservation
    assert len(emit_calls) == 2
    assert emit_calls[0][1]["cls"] == "NormalEvent"
    assert emit_calls[1][1]["cls"] == "AgentStateChangedObservation"


@pytest.mark.asyncio
async def test_join_conversation_failure_raises(monkeypatch):
    environ = {"QUERY_STRING": "conversation_id=convFail"}

    # Basic valid setup - validator method
    class Validator:
        async def validate(self, conversation_id, cookies_str, authorization_header):
            return "userid"

    monkeypatch.setattr(MODULE, "_invalid_session_api_key", lambda qp: False)
    monkeypatch.setattr(MODULE, "create_conversation_validator", lambda: Validator())

    # Minimal AsyncEventStoreWrapper that yields nothing
    class EmptyAsyncIter:
        def __init__(self, es, start):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    monkeypatch.setattr(MODULE, "AsyncEventStoreWrapper", EmptyAsyncIter)
    monkeypatch.setattr(MODULE, "event_to_dict", lambda ev: {})

    # setup returns init data
    async def fake_setup(user_id, conversation_id, providers_set):
        return {}

    monkeypatch.setattr(MODULE, "setup_init_conversation_settings", fake_setup)

    # join_conversation returns None to indicate failure
    async def fake_join_conversation(conversation_id, connection_id, init_data, user_id):
        return None

    monkeypatch.setattr(MODULE.conversation_manager, "join_conversation", fake_join_conversation)

    # capture create_task calls
    created = []

    async def fake_disconnect(conn_id):
        created.append(("d", conn_id))

    def fake_create_task(coro):
        created.append(("t", coro))
        return "task"

    monkeypatch.setattr(MODULE, "sio", type("SIO", (), {"disconnect": fake_disconnect, "emit": lambda *a, **k: None, "event": MODULE.sio.event}))
    monkeypatch.setattr(MODULE.asyncio, "create_task", fake_create_task)

    with pytest.raises(MODULE.ConnectionRefusedError):
        await MODULE.connect("conn-fail-join", environ)

    assert any(entry[0] == "t" for entry in created)
