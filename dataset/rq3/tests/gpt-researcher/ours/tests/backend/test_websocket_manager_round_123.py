import asyncio
import pytest

from backend.server.websocket_manager import WebSocketManager


class FakeWebSocket:
    def __init__(self, accept_behavior=None):
        # accept_behavior: None => succeed, Exception instance => raise
        self.accept_behavior = accept_behavior

    async def accept(self):
        if isinstance(self.accept_behavior, Exception):
            raise self.accept_behavior
        return None

    def __repr__(self):
        return f"<FakeWebSocket id={id(self)}>"


class DummyTask:
    def __init__(self, marker="dummy"):
        self.marker = marker

    def __repr__(self):
        return f"DummyTask({self.marker})"


@pytest.mark.asyncio
async def test_connect_success_round_123(monkeypatch):
    """Happy path: accept succeeds, queue and task are set up."""
    manager = WebSocketManager()
    ws = FakeWebSocket()

    # Patch start_sender to a simple coroutine so create_task receives a coroutine object
    async def fake_start_sender(websocket):
        # Validate that the websocket passed is the same object
        assert websocket is ws
        # simulate a trivial coroutine
        await asyncio.sleep(0)
        return "started"

    monkeypatch.setattr(manager, "start_sender", fake_start_sender)

    created = {}

    def fake_create_task(coro):
        # record that create_task was called with a coroutine
        created['coro_repr'] = repr(coro)
        return DummyTask("created")

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    await manager.connect(ws)

    # Assertions: websocket accepted and active_connections updated
    assert ws in manager.active_connections
    # message_queues should have a queue for this websocket
    assert ws in manager.message_queues
    # sender_tasks should contain the DummyTask we returned
    assert isinstance(manager.sender_tasks[ws], DummyTask)
    # ensure create_task was invoked with some coroutine
    assert 'coro_repr' in created


@pytest.mark.asyncio
async def test_connect_exception_after_append_triggers_disconnect_round_123(monkeypatch):
    """If create_task raises after the websocket has been appended, connect should catch
    the exception and call disconnect when the websocket is still in active_connections.
    """
    manager = WebSocketManager()
    ws = FakeWebSocket()

    # make start_sender exist but it won't be reached because create_task will raise
    async def fake_start_sender(websocket):
        await asyncio.sleep(0)

    monkeypatch.setattr(manager, "start_sender", fake_start_sender)

    # create_task will raise to force the except branch after append
    def raising_create_task(coro):
        raise RuntimeError("create_task failure")

    monkeypatch.setattr(asyncio, "create_task", raising_create_task)

    disconnect_called = {"called": False}

    async def fake_disconnect(websocket):
        # simulate cleanup that real disconnect might perform
        disconnect_called["called"] = True
        if websocket in manager.active_connections:
            manager.active_connections.remove(websocket)
        # also remove other structures to mimic expected cleanup
        manager.message_queues.pop(websocket, None)
        manager.sender_tasks.pop(websocket, None)

    monkeypatch.setattr(manager, "disconnect", fake_disconnect)

    # Run connect; it should handle the create_task exception internally and call disconnect
    await manager.connect(ws)

    assert disconnect_called["called"] is True
    # After disconnect, websocket should no longer be considered active
    assert ws not in manager.active_connections


@pytest.mark.asyncio
async def test_connect_exception_before_append_no_disconnect_round_123(monkeypatch):
    """If accept itself raises, the websocket was never appended; disconnect should not be called."""
    manager = WebSocketManager()
    ws = FakeWebSocket(accept_behavior=RuntimeError("accept failed"))

    # Ensure create_task is a no-op if somehow reached (shouldn't be)
    monkeypatch.setattr(asyncio, "create_task", lambda coro: DummyTask("should_not_be_used"))

    disconnect_called = {"called": False}

    async def fake_disconnect(websocket):
        disconnect_called["called"] = True

    monkeypatch.setattr(manager, "disconnect", fake_disconnect)

    # Run connect; accept raises and connect should catch it without calling disconnect
    await manager.connect(ws)

    assert disconnect_called["called"] is False
    # websocket should never have been added
    assert ws not in manager.active_connections
