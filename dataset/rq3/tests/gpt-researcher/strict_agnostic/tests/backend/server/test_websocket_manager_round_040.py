import asyncio
import pytest

from backend.server.websocket_manager import WebSocketManager


class DummyWebSocket:
    def __init__(self, *, close_raises=False):
        self.closed = False
        self.close_called = 0
        self._close_raises = close_raises

    async def close(self):
        # simulate async close, possibly raising
        self.close_called += 1
        if self._close_raises:
            raise RuntimeError("close failed")
        self.closed = True


class DummyTask:
    def __init__(self, *, cancel_raises=False):
        self.cancel_called = 0
        self._cancel_raises = cancel_raises

    def cancel(self):
        self.cancel_called += 1
        if self._cancel_raises:
            raise RuntimeError("cancel failed")


class DummyQueue:
    def __init__(self, *, put_raises=False):
        self.items = []
        self.put_called = 0
        self._put_raises = put_raises

    async def put(self, item):
        self.put_called += 1
        if self._put_raises:
            raise RuntimeError("put failed")
        self.items.append(item)


class ActiveConnectionsRaiser:
    """Custom container that raises when checked for membership to trigger outer except."""

    def __contains__(self, item):
        raise RuntimeError("contains failed")


@pytest.mark.asyncio
async def test_disconnect_successful_round_040():
    """WebSocket present in all maps: cancel succeeds, put succeeds, close succeeds.

    Assertions:
    - websocket removed from active_connections
    - sender_tasks and message_queues entries removed
    - websocket.close was awaited and succeeded
    """
    manager = WebSocketManager()

    ws = DummyWebSocket()

    # Ensure manager starts with expected structures
    # If __init__ already created these mappings, use them; otherwise set them.
    manager.active_connections.add(ws) if hasattr(manager, "active_connections") and hasattr(manager.active_connections, "add") else setattr(manager, "active_connections", [ws])

    # Normalize active_connections to a mutable list for this test
    if not isinstance(manager.active_connections, list):
        manager.active_connections = [ws]

    manager.sender_tasks = {ws: DummyTask(cancel_raises=False)}
    manager.message_queues = {ws: DummyQueue(put_raises=False)}

    # Call disconnect
    await manager.disconnect(ws)

    # After disconnect: websocket removed from active_connections
    assert ws not in manager.active_connections

    # sender_tasks and message_queues cleaned up
    assert ws not in manager.sender_tasks
    assert ws not in manager.message_queues

    # close was called once and succeeded
    assert ws.close_called == 1
    assert ws.closed is True


@pytest.mark.asyncio
async def test_disconnect_with_cancel_and_put_exceptions_and_close_handled_round_040():
    """Cancel() and queue.put() raise; cancel exception path exercised; close raises and is caught.

    Assertions:
    - manager still removes sender_tasks and message_queues entries in finally
    - websocket.close was attempted (and raised) but handled by the function
    """
    manager = WebSocketManager()

    # Normalize active_connections to a mutable list
    ws = DummyWebSocket(close_raises=True)
    if not hasattr(manager, "active_connections") or isinstance(manager.active_connections, (set, dict)) is False:
        manager.active_connections = [ws]
    else:
        manager.active_connections = [ws]

    # Create sender task that will raise on cancel and queue that will raise on put
    manager.sender_tasks = {ws: DummyTask(cancel_raises=True)}
    manager.message_queues = {ws: DummyQueue(put_raises=True)}

    # Call disconnect: exceptions inside cancel/put should be caught and logged, not propagated
    await manager.disconnect(ws)

    # Ensure entries cleaned up
    assert ws not in manager.sender_tasks
    assert ws not in manager.message_queues

    # close was attempted once but raised (so closed remains False)
    assert ws.close_called == 1
    assert ws.closed is False


@pytest.mark.asyncio
async def test_disconnect_outer_exception_triggers_fallback_close_round_040():
    """If the initial membership check raises, outer except handles it and attempts to close websocket.

    Use a custom active_connections that raises during __contains__ to force the outer except path.
    Assertions:
    - websocket.close is attempted in the outer except branch
    - if close succeeds, websocket.closed is True; if close raises, it is swallowed (no exception)
    """
    manager = WebSocketManager()

    ws = DummyWebSocket(close_raises=False)

    # Replace active_connections with object that raises on membership check
    manager.active_connections = ActiveConnectionsRaiser()

    # Ensure sender_tasks and message_queues exist as empty mappings
    manager.sender_tasks = {}
    manager.message_queues = {}

    # Call disconnect: membership check will raise and outer except should attempt to close
    await manager.disconnect(ws)

    # close was attempted once and succeeded
    assert ws.close_called == 1
    assert ws.closed is True
