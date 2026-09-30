import types
import pytest
from types import SimpleNamespace

import importlib

from openhands.server.session.session import WebSession
from openhands.server.constants import ROOM_KEY


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.error_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


class DummySio:
    def __init__(self, emit_impl=None, rooms=None):
        # manager.rooms should be a dict of namespace -> dict
        self.manager = SimpleNamespace(rooms=rooms if rooms is not None else {'/': {}})
        self._emit_impl = emit_impl
        self.emit_calls = []

    async def emit(self, name, data, to=None):
        self.emit_calls.append({'name': name, 'data': data, 'to': to})
        if self._emit_impl is not None:
            return await self._emit_impl(name, data, to)
        return None


@pytest.mark.asyncio
async def test_send_returns_false_when_not_alive_round_044():
    # Create a WebSession instance without running __init__ and set is_alive False
    session_mod = importlib.import_module('openhands.server.session.session')
    ws = object.__new__(WebSession)
    ws.is_alive = False

    # Calling _send should short-circuit and return False without touching other attributes
    result = await ws._send({'k': 'v'})
    assert result is False


@pytest.mark.asyncio
async def test_send_emits_and_sets_last_active_round_044(monkeypatch):
    # Prepare module and deterministic time/sleep
    session_mod = importlib.import_module('openhands.server.session.session')

    # Deterministic time: always return 1000.0
    monkeypatch.setattr(session_mod.time, 'time', lambda: 1000.0)

    # Replace asyncio.sleep with a no-op coroutine to avoid delays
    async def fake_sleep(duration):
        fake_sleep.calls.append(duration)
        return None

    fake_sleep.calls = []
    monkeypatch.setattr(session_mod.asyncio, 'sleep', fake_sleep)

    # Build a WebSession instance and required attributes
    ws = object.__new__(WebSession)
    ws.is_alive = True
    ws.sid = 'S123'
    ws._wait_websocket_initial_complete = True

    # config with client_wait_timeout attribute
    ws.config = SimpleNamespace(client_wait_timeout=30)

    # dummy logger
    ws.logger = DummyLogger()

    # Prepare sio whose manager.rooms already contains the room -> loop will break immediately
    room_key = ROOM_KEY.format(sid=ws.sid)
    rooms = {'/': {room_key: {'present': True}}}

    emitted = {}

    async def emit_impl(name, data, to):
        emitted['name'] = name
        emitted['data'] = data
        emitted['to'] = to
        return None

    sio = DummySio(emit_impl=emit_impl, rooms=rooms)
    ws.sio = sio

    # Invoke _send
    payload = {'hello': 'world'}
    result = await ws._send(payload)

    # Assertions:
    assert result is True
    # last_active_ts should be int(1000.0)
    assert getattr(ws, 'last_active_ts') == 1000
    # _wait_websocket_initial_complete should be cleared
    assert ws._wait_websocket_initial_complete is False
    # Emit was called exactly once with correct args
    assert emitted['name'] == 'oh_event'
    assert emitted['data'] is payload
    assert emitted['to'] == ROOM_KEY.format(sid=ws.sid)
    # The final small sleep for flushing was invoked with 0.001
    assert 0.001 in fake_sleep.calls


@pytest.mark.asyncio
async def test_send_handles_runtime_error_round_044(monkeypatch):
    # Prepare module and deterministic sleep/time
    session_mod = importlib.import_module('openhands.server.session.session')
    monkeypatch.setattr(session_mod.time, 'time', lambda: 2000.0)

    async def fake_sleep(duration):
        return None

    monkeypatch.setattr(session_mod.asyncio, 'sleep', fake_sleep)

    # Create session instance that will raise RuntimeError when emitting
    ws = object.__new__(WebSession)
    ws.is_alive = True
    ws.sid = 'SERR'
    # Skip websocket waiting to go straight to emit
    ws._wait_websocket_initial_complete = False
    ws.config = SimpleNamespace(client_wait_timeout=5)

    # Logger to capture error
    ws.logger = DummyLogger()

    async def emit_raise(name, data, to):
        raise RuntimeError('emit-failed')

    sio = DummySio(emit_impl=emit_raise, rooms={'/': {}})
    ws.sio = sio

    result = await ws._send({'err': 1})

    # Expect the method to catch RuntimeError, log it, mark is_alive False and return False
    assert result is False
    assert ws.is_alive is False
    assert len(ws.logger.error_calls) == 1
    assert 'emit-failed' in ws.logger.error_calls[0]
