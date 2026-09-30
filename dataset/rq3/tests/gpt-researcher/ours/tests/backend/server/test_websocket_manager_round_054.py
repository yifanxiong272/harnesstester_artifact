import asyncio
import pytest
from types import SimpleNamespace
from backend.server.websocket_manager import WebSocketManager

class FakeWebSocket:
    def __init__(self, send_raises=None):
        # send_raises: exception instance to raise when send_text called
        self.sent = []
        self.send_raises = send_raises

    async def send_text(self, text):
        if self.send_raises is not None:
            raise self.send_raises
        # record sent messages for assertions
        self.sent.append(text)


@pytest.mark.asyncio
async def test_queue_none_returns_round_054():
    # Create manager without running __init__ to control attributes precisely
    manager = WebSocketManager.__new__(WebSocketManager)
    # No queue for this websocket -> get should return None and function should return early
    websocket = object()
    manager.message_queues = {}

    # Should simply return without error
    result = await manager.start_sender(websocket)
    assert result is None


@pytest.mark.asyncio
async def test_sends_pong_and_message_then_shutdown_round_054():
    manager = WebSocketManager.__new__(WebSocketManager)
    websocket = FakeWebSocket()
    queue = asyncio.Queue()

    # Put ping, then a normal message, then shutdown signal (None)
    await queue.put("ping")
    await queue.put("hello")
    await queue.put(None)

    manager.message_queues = {websocket: queue}
    # Active connections contains the websocket so messages are sent
    manager.active_connections = {websocket}

    await manager.start_sender(websocket)

    # Expect ping->pong translation, then the original message
    assert websocket.sent == ["pong", "hello"]


@pytest.mark.asyncio
async def test_breaks_when_websocket_not_active_round_054():
    manager = WebSocketManager.__new__(WebSocketManager)
    websocket = FakeWebSocket()
    queue = asyncio.Queue()

    # Put a single message followed by shutdown; because websocket is not active,
    # the loop should break after consuming the message and should not call send_text
    await queue.put("hello")
    await queue.put(None)

    manager.message_queues = {websocket: queue}
    # Active connections does NOT include websocket
    manager.active_connections = set()

    await manager.start_sender(websocket)

    # send_text should not be called
    assert websocket.sent == []


@pytest.mark.asyncio
async def test_exception_in_send_text_prints_and_breaks_round_054(capsys):
    manager = WebSocketManager.__new__(WebSocketManager)
    # send_text will raise ValueError('boom') to trigger the exception branch
    websocket = FakeWebSocket(send_raises=ValueError('boom'))
    queue = asyncio.Queue()

    await queue.put("oops")
    # Put a shutdown token as well; but after exception the loop should break and
    # not process further items
    await queue.put(None)

    manager.message_queues = {websocket: queue}
    manager.active_connections = {websocket}

    await manager.start_sender(websocket)

    captured = capsys.readouterr()
    # The code prints a formatted error message containing the exception message
    assert "Error in sender task: boom" in captured.out
    # Because send_text raised, nothing should have been appended to sent
    assert websocket.sent == []
