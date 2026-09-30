import importlib
import asyncio
from types import SimpleNamespace
import pytest

# Load the module under test
session_mod = importlib.import_module("openhands.server.session.session")
WebSession = session_mod.WebSession
ROOM_KEY = session_mod.ROOM_KEY

# Small async no-op to replace real sleeps in the module under test
async def _async_noop(duration=0):
    # Intentionally do nothing to keep tests fast and deterministic
    return None

class CaptureLogger:
    def __init__(self):
        self.debug_msgs = []
        self.error_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(str(msg))

    def error(self, msg):
        self.error_msgs.append(str(msg))


def test_send_returns_false_when_not_alive_round_044(monkeypatch):
    """If the session reports not alive, _send should return False immediately."""
    # Ensure no real sleeps are used
    monkeypatch.setattr(session_mod.asyncio, "sleep", _async_noop)

    fake_self = SimpleNamespace(is_alive=False)

    # Call the coroutine directly via asyncio.run for deterministic execution
    result = asyncio.run(WebSession._send(fake_self, {"k": "v"}))
    assert result is False


def test_send_without_sio_sets_last_active_and_returns_true_round_044(monkeypatch):
    """When sio is None, the method should skip websocket logic, sleep briefly and set last_active_ts."""
    # Patch sleep and time to deterministic values
    monkeypatch.setattr(session_mod.asyncio, "sleep", _async_noop)
    monkeypatch.setattr(session_mod.time, "time", lambda: 123456)

    logger = CaptureLogger()
    config = SimpleNamespace(client_wait_timeout=30)

    fake_self = SimpleNamespace(
        is_alive=True,
        sio=None,
        config=config,
        logger=logger,
        sid="sid-no-sio",
        _wait_websocket_initial_complete=False,
        last_active_ts=None,
    )

    result = asyncio.run(WebSession._send(fake_self, {"payload": 1}))

    assert result is True
    # last_active_ts should be set from the patched time.time()
    assert fake_self.last_active_ts == 123456
    # No error messages should have been logged
    assert logger.error_msgs == []


def test_send_with_sio_emit_and_room_exists_round_044(monkeypatch):
    """If the manager.rooms contains the session's room key, the send should break the wait loop and emit once."""
    # Patch sleep and time so the loop is deterministic and fast
    monkeypatch.setattr(session_mod.asyncio, "sleep", _async_noop)
    monkeypatch.setattr(session_mod.time, "time", lambda: 200000)

    logger = CaptureLogger()
    config = SimpleNamespace(client_wait_timeout=5)
    sid = "sid-room-exists"

    # Prepare a fake manager.rooms structure that contains the room key
    room_name = ROOM_KEY.format(sid=sid)
    manager = SimpleNamespace(rooms={'/': {room_name: {'dummy': True}}})

    emitted = []

    async def fake_emit(event_name, data, to=None):
        emitted.append((event_name, data, to))

    sio = SimpleNamespace(manager=manager, emit=fake_emit)

    fake_self = SimpleNamespace(
        is_alive=True,
        sio=sio,
        config=config,
        logger=logger,
        sid=sid,
        _wait_websocket_initial_complete=True,
        last_active_ts=None,
    )

    payload = {"x": 42}
    result = asyncio.run(WebSession._send(fake_self, payload))

    assert result is True
    # After successful send, the room-based emit should have been called once
    assert len(emitted) == 1
    name, data_sent, to_arg = emitted[0]
    assert name == 'oh_event'
    assert data_sent is payload
    assert to_arg == ROOM_KEY.format(sid=sid)
    # The flag should be cleared
    assert fake_self._wait_websocket_initial_complete is False
    # last_active_ts should be set from patched time
    assert fake_self.last_active_ts == 200000


def test_send_emit_raises_runtime_error_round_044(monkeypatch):
    """If sio.emit raises RuntimeError, _send should catch it, set is_alive False and return False, logging the error."""
    monkeypatch.setattr(session_mod.asyncio, "sleep", _async_noop)
    monkeypatch.setattr(session_mod.time, "time", lambda: 999999)

    logger = CaptureLogger()
    config = SimpleNamespace(client_wait_timeout=5)
    sid = "sid-emit-error"

    manager = SimpleNamespace(rooms={'/': {ROOM_KEY.format(sid=sid): {'ok': True}}})

    async def raising_emit(event_name, data, to=None):
        raise RuntimeError("boom")

    sio = SimpleNamespace(manager=manager, emit=raising_emit)

    fake_self = SimpleNamespace(
        is_alive=True,
        sio=sio,
        config=config,
        logger=logger,
        sid=sid,
        _wait_websocket_initial_complete=True,
        last_active_ts=None,
    )

    result = asyncio.run(WebSession._send(fake_self, {"err": True}))

    assert result is False
    # is_alive should be flipped to False on RuntimeError
    assert fake_self.is_alive is False
    # An error message should have been logged mentioning sending data
    assert any("Error sending data to websocket" in m for m in logger.error_msgs)
