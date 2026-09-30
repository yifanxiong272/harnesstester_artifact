import asyncio
import time
from types import SimpleNamespace
from openhands.server.constants import ROOM_KEY
from openhands.server.session.session import WebSession


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.error_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


class DummyConfig:
    def __init__(self, client_wait_timeout=0.5):
        # short timeout to keep tests fast
        self.client_wait_timeout = client_wait_timeout


class DummySio:
    def __init__(self, rooms=None, emit_coro=None):
        # manager with rooms mapping used by the logic
        self.manager = SimpleNamespace(rooms=(rooms or {}))
        # emit_coro should be an async callable
        self._emit_coro = emit_coro or (lambda *a, **k: None)

    async def emit(self, *args, **kwargs):
        # delegate to provided coroutine for observability or to raise
        return await self._emit_coro(*args, **kwargs)


# Helper to build a WebSession instance without calling its constructor
def make_session_stub(
    *,
    is_alive=True,
    sio=None,
    sid="test-sid",
    wait_initial_complete=False,
    client_wait_timeout=0.5,
):
    ws = WebSession.__new__(WebSession)
    ws.is_alive = is_alive
    ws.sio = sio
    ws.sid = sid
    ws._wait_websocket_initial_complete = wait_initial_complete
    ws.config = DummyConfig(client_wait_timeout=client_wait_timeout)
    ws.logger = DummyLogger()
    ws.last_active_ts = 0
    return ws


def test_send_returns_false_when_not_alive_round_044():
    # Arrange: session not alive should immediately return False
    ws = make_session_stub(is_alive=False, sio=None)

    # Act
    result = asyncio.run(ws._send({}))

    # Assert
    assert result is False
    # last_active_ts should remain unchanged when not alive
    assert ws.last_active_ts == 0


def test_send_without_sio_sets_last_active_and_returns_true_round_044():
    # Arrange: alive session but no sio -> skip sio branch and return True
    ws = make_session_stub(is_alive=True, sio=None)
    before = int(time.time())

    # Act
    result = asyncio.run(ws._send({"k": "v"}))

    # Assert
    assert result is True
    # last_active_ts is set to an integer timestamp not earlier than before
    assert isinstance(ws.last_active_ts, int)
    assert ws.last_active_ts >= before


def test_send_with_sio_emit_called_and_wait_websocket_initial_complete_round_044():
    # Arrange: provide sio where the room already exists so the while loop breaks immediately
    sid = "session-123"
    rooms = {"/": {ROOM_KEY.format(sid=sid): {"dummy": True}}}

    emitted = {}

    async def emit_ok(event_name, data, to=None):
        # record what was emitted
        emitted['event_name'] = event_name
        emitted['data'] = data
        emitted['to'] = to
        return None

    sio = DummySio(rooms=rooms, emit_coro=emit_ok)
    ws = make_session_stub(
        is_alive=True, sio=sio, sid=sid, wait_initial_complete=True, client_wait_timeout=1.0
    )

    # Act
    result = asyncio.run(ws._send({"a": 1}))

    # Assert
    assert result is True
    # The _wait_websocket_initial_complete flag should be cleared after the call
    assert ws._wait_websocket_initial_complete is False
    # Emit was called with expected event name and the right target (ROOM_KEY formatted)
    assert emitted.get('event_name') == 'oh_event'
    assert emitted.get('data') == {"a": 1}
    assert emitted.get('to') == ROOM_KEY.format(sid=sid)
    # last_active_ts updated
    assert isinstance(ws.last_active_ts, int)
    assert ws.last_active_ts > 0


def test_send_handles_runtime_error_from_emit_and_marks_not_alive_round_044():
    # Arrange: sio.emit raises RuntimeError which should be caught and cause is_alive to be False
    sid = "session-err"

    async def emit_error(*args, **kwargs):
        raise RuntimeError("simulated emit failure")

    sio = DummySio(rooms={"/": {}}, emit_coro=emit_error)
    ws = make_session_stub(is_alive=True, sio=sio, sid=sid, wait_initial_complete=False)

    # Act
    result = asyncio.run(ws._send({"x": "y"}))

    # Assert: should return False and mark session as not alive
    assert result is False
    assert ws.is_alive is False
    # Logger recorded an error message including the exception text
    assert any("simulated emit failure" in msg for msg in ws.logger.error_calls)
