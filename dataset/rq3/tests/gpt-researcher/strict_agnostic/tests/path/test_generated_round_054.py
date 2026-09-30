import asyncio
import pytest

from backend.server.websocket_manager import WebSocketManager


class MockWebSocket:
    """Minimal mock WebSocket with an async send_text method.

    Instances record sent messages in .sent. Optionally raise on send to
    exercise error handling.
    """

    def __init__(self, raise_on_send: bool = False):
        self.sent = []
        self._raise = raise_on_send

    async def send_text(self, text):
        if self._raise:
            raise RuntimeError("simulated send failure")
        # emulate async send latency deterministically
        await asyncio.sleep(0)
        self.sent.append(text)


def _ensure_active(manager: WebSocketManager, ws):
    """Add ws to manager.active_connections in a robust way for sets/lists."""
    ac = getattr(manager, "active_connections", None)
    if ac is None:
        # If attribute doesn't exist, create a set
        manager.active_connections = {ws}
        return
    try:
        ac.add(ws)  # set-like
    except Exception:
        try:
            ac.append(ws)  # list-like
        except Exception:
            # fallback: reassign
            manager.active_connections = {ws}


def _ensure_not_active(manager: WebSocketManager, ws):
    ac = getattr(manager, "active_connections", None)
    if ac is None:
        manager.active_connections = set()
        return
    try:
        ac.discard(ws)
    except Exception:
        try:
            while ws in ac:
                ac.remove(ws)
        except Exception:
            # can't remove; ignore
            pass


def test_no_queue_round_054():
    """When there is no queue for the websocket, start_sender returns immediately."""
    manager = WebSocketManager()
    ws = object()  # simple key that won't be in manager.message_queues

    # guard: ensure no queue exists for this websocket
    manager.message_queues.pop(ws, None)

    # run synchronously; should return without blocking
    asyncio.run(manager.start_sender(ws))

    # observable: still no queue created and function returned
    assert ws not in manager.message_queues


def test_shutdown_signal_round_054():
    """If the queue yields None right away, start_sender breaks (shutdown signal)."""
    manager = WebSocketManager()
    ws = MockWebSocket()
    q = asyncio.Queue()
    q.put_nowait(None)  # immediate shutdown

    manager.message_queues[ws] = q

    # should exit quickly on receiving None
    asyncio.run(manager.start_sender(ws))

    # No messages should have been sent
    assert ws.sent == []


def test_ping_and_message_round_054():
    """When active and messages 'ping' and other text arrive, they are sent as 'pong' and same text."""
    manager = WebSocketManager()
    ws = MockWebSocket()
    q = asyncio.Queue()

    # queue messages in order: ping -> hello -> shutdown
    q.put_nowait("ping")
    q.put_nowait("hello")
    q.put_nowait(None)

    manager.message_queues[ws] = q
    _ensure_active(manager, ws)

    # run the sender which will process all queued messages
    asyncio.run(manager.start_sender(ws))

    # verify correct sends in order
    assert ws.sent == ["pong", "hello"]


def test_not_active_connection_round_054():
    """If websocket is not in active_connections, the loop breaks and no messages are sent."""
    manager = WebSocketManager()
    ws = MockWebSocket()
    q = asyncio.Queue()
    q.put_nowait("hi")
    q.put_nowait(None)

    manager.message_queues[ws] = q
    # ensure not active
    _ensure_not_active(manager, ws)

    asyncio.run(manager.start_sender(ws))

    # because ws was not active, the message should not have been sent
    assert ws.sent == []


def test_send_raises_exception_round_054(capsys):
    """If send_text raises, the exception is caught and an error message is printed, then the sender breaks."""
    manager = WebSocketManager()
    ws = MockWebSocket(raise_on_send=True)
    q = asyncio.Queue()
    q.put_nowait("will-raise")

    manager.message_queues[ws] = q
    _ensure_active(manager, ws)

    # run; the mocked send_text will raise and should be caught inside start_sender
    asyncio.run(manager.start_sender(ws))

    captured = capsys.readouterr()
    # the module prints an error message including the prefix; assert presence
    assert "Error in sender task" in captured.out or "Error in sender task" in captured.err
