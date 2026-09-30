import asyncio
import logging
import pytest

from backend.server import websocket_manager
from backend.server.websocket_manager import WebSocketManager

# Helper test doubles
class DummyWebSocket:
    def __init__(self, *, close_raises=False):
        self.closed = False
        self._close_raises = close_raises

    def __repr__(self):
        return f"DummyWebSocket(id={id(self)})"

    async def close(self):
        if self._close_raises:
            raise RuntimeError("close failed")
        self.closed = True


class DummyQueue:
    def __init__(self, *, put_raises=False):
        self.items = []
        self.put_raises = put_raises

    async def put(self, item):
        if self.put_raises:
            raise RuntimeError("put failed")
        self.items.append(item)


class DummySenderTask:
    def __init__(self, *, cancel_raises=False):
        self.cancel_called = False
        self.cancel_raises = cancel_raises

    def cancel(self):
        self.cancel_called = True
        if self.cancel_raises:
            raise RuntimeError("cancel failed")


class BadActiveConnections:
    """A list-like object whose remove() raises to trigger the outer except block."""
    def __contains__(self, item):
        return True

    def remove(self, item):
        raise RuntimeError("remove failed")


@pytest.mark.asyncio
async def test_disconnect_success_round_040(caplog):
    """Normal path: sender task canceled, queue put(None) succeeds, close succeeds.

    Assertions:
    - sender task.cancel was called
    - message queue received None
    - manager no longer contains the websocket in sender_tasks or message_queues
    - websocket.closed is True
    """
    caplog.set_level(logging.DEBUG)

    # Build manager without running __init__ to control internal state
    mgr = WebSocketManager.__new__(WebSocketManager)
    ws = DummyWebSocket(close_raises=False)

    mgr.active_connections = [ws]
    q = DummyQueue()
    task = DummySenderTask()
    mgr.sender_tasks = {ws: task}
    mgr.message_queues = {ws: q}

    await mgr.disconnect(ws)

    # state assertions
    assert task.cancel_called is True, "sender task.cancel was not called"
    assert q.items == [None], "message queue did not receive the sentinel None"
    assert ws not in mgr.sender_tasks, "sender_tasks entry was not removed"
    assert ws not in mgr.message_queues, "message_queues entry was not removed"
    assert ws.closed is True, "websocket.close was not awaited successfully"


@pytest.mark.asyncio
async def test_disconnect_cancel_and_close_raise_round_040(caplog):
    """Inner try: cancel / put raise -> logged error, finally deletes sender_tasks.
    Then websocket.close raises and is logged as info. Ensure function completes.
    """
    caplog.set_level(logging.DEBUG)

    mgr = WebSocketManager.__new__(WebSocketManager)
    ws = DummyWebSocket(close_raises=True)  # make close raise to hit info branch

    mgr.active_connections = [ws]

    # Make cancel and put both raise to exercise the inner except
    task = DummySenderTask(cancel_raises=True)
    q = DummyQueue(put_raises=True)

    mgr.sender_tasks = {ws: task}
    mgr.message_queues = {ws: q}

    await mgr.disconnect(ws)

    # sender_tasks entry must be removed in finally block
    assert ws not in mgr.sender_tasks
    # message_queues entry must be removed after finally
    assert ws not in mgr.message_queues

    # Check logs: inner exception should have produced an error about canceling
    assert any("Error canceling sender task" in rec.getMessage() for rec in caplog.records), (
        "expected 'Error canceling sender task' in logs"
    )
    # And close raised should have produced an info log about already closed
    assert any("WebSocket already closed" in rec.getMessage() for rec in caplog.records), (
        "expected 'WebSocket already closed' in logs"
    )


@pytest.mark.asyncio
async def test_disconnect_remove_raises_outer_except_round_040(caplog):
    """If removing the websocket from active_connections raises, the outer except
    path should log an error and still attempt to close the websocket. If the
    close also raises, that exception should be swallowed and the call should
    not propagate.
    """
    caplog.set_level(logging.DEBUG)

    mgr = WebSocketManager.__new__(WebSocketManager)
    # Use a websocket whose close also raises to exercise the nested except at the end
    ws = DummyWebSocket(close_raises=True)

    # active_connections.remove will raise
    mgr.active_connections = BadActiveConnections()

    # No sender_tasks or message_queues relevant for this test
    mgr.sender_tasks = {}
    mgr.message_queues = {}

    # Should not raise despite the remove failing and websocket.close failing
    await mgr.disconnect(ws)

    # Logs should contain the outer error message
    assert any("Error during WebSocket disconnection" in rec.getMessage() for rec in caplog.records), (
        "expected outer 'Error during WebSocket disconnection' in logs"
    )
