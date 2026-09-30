import asyncio
import time
import types
import pytest

from openhands.server.constants import ROOM_KEY
from openhands.server.session.session import WebSession

# Capture the real asyncio.sleep before any monkeypatching to avoid recursion
_real_sleep = asyncio.sleep


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.error_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)


class DummyConfig:
    def __init__(self, client_wait_timeout=5):
        self.client_wait_timeout = client_wait_timeout


class DynamicRooms:
    """Rooms object whose '/'->.get(ROOM_KEY) returns falsy for N calls and truthy afterwards.

    Each call to the returned proxy's get() increments an internal counter. This lets tests
    drive the loop in _send to iterate a controlled number of times without real sleeping.
    """

    def __init__(self, sid, good_after_calls=12):
        self.calls = 0
        self.sid = sid
        self.good_after_calls = good_after_calls

    class RoomProxy:
        def __init__(self, parent):
            self._parent = parent

        def get(self, key, default=None):
            # called with ROOM_KEY.format(sid=self.sid)
            self._parent.calls += 1
            if self._parent.calls >= self._parent.good_after_calls:
                # return a truthy value for the desired room key
                return True
            return None

    def get(self, key, default=None):
        # return a proxy that implements .get(...) as a dict-like
        return DynamicRooms.RoomProxy(self)


class DummySio:
    def __init__(self, sid, good_after_calls=12, raise_on_emit=False):
        self.manager = types.SimpleNamespace(rooms=DynamicRooms(sid, good_after_calls))
        self.emitted = []
        self.raise_on_emit = raise_on_emit

    async def emit(self, event, data, to=None):
        if self.raise_on_emit:
            raise RuntimeError("simulated emit failure")
        # record emission for assertions
        self.emitted.append((event, data, to))


# Patch asyncio.sleep to a deterministic no-op that uses the original sleep to avoid recursion
async def _noop_sleep(duration):
    # use the original captured sleep to avoid calling the monkeypatched one
    await _real_sleep(0)


@pytest.mark.asyncio
async def test_send_returns_false_when_not_alive_round_044(monkeypatch):
    """When session.is_alive is False, _send should return False immediately."""
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    fake_session = types.SimpleNamespace()
    fake_session.is_alive = False
    fake_session.sid = "sid-1"
    fake_session.config = DummyConfig()
    fake_session.logger = DummyLogger()
    fake_session.sio = None
    fake_session._wait_websocket_initial_complete = True
    fake_session.last_active_ts = None

    # call unbound coroutine with our fake session as self
    result = await WebSession._send(fake_session, {"x": 1})

    assert result is False
    # nothing should have been emitted, last_active_ts remains unchanged
    assert fake_session.last_active_ts is None
    # no error logged
    assert fake_session.logger.error_msgs == []


@pytest.mark.asyncio
async def test_send_without_sio_round_044(monkeypatch):
    """If sio is None, the websocket-specific waiting/emit block is skipped and
    function should return True while updating last_active_ts."""
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    fake_session = types.SimpleNamespace()
    fake_session.is_alive = True
    fake_session.sid = "sid-2"
    fake_session.config = DummyConfig(client_wait_timeout=1)
    fake_session.logger = DummyLogger()
    fake_session.sio = None
    fake_session._wait_websocket_initial_complete = True
    fake_session.last_active_ts = 0

    before = int(time.time())
    result = await WebSession._send(fake_session, {"hello": "world"})
    after = int(time.time())

    assert result is True
    # last_active_ts should have been updated to a current-ish integer timestamp
    assert isinstance(fake_session.last_active_ts, int)
    assert before - 1 <= fake_session.last_active_ts <= after + 1
    # because sio is None, there should be no emits


@pytest.mark.asyncio
async def test_send_waits_and_emits_then_returns_true_round_044(monkeypatch):
    """Exercise the loop branch where sio exists and the room appears after several polls.
    This also exercises the progressive backoff path (switching from 0.1 to 1.0) and
    the logging of waiting messages.
    """
    # keep asyncio.sleep deterministic and fast
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    sid = "sid-3"
    # make the room appear after 12 checks to force iterations and hit the >10 branch
    sio = DummySio(sid, good_after_calls=12, raise_on_emit=False)

    fake_session = types.SimpleNamespace()
    fake_session.is_alive = True
    fake_session.sid = sid
    # long timeout so time-based exit won't happen during our tight loop
    fake_session.config = DummyConfig(client_wait_timeout=1000)
    logger = DummyLogger()
    fake_session.logger = logger
    fake_session.sio = sio
    fake_session._wait_websocket_initial_complete = True
    fake_session.last_active_ts = None

    data = {"k": "v"}
    result = await WebSession._send(fake_session, data)

    assert result is True
    # sio.emit must have been called once with oh_event and correct 'to' ROOM_KEY
    assert len(sio.emitted) == 1
    emitted_event, emitted_data, emitted_to = sio.emitted[0]
    assert emitted_event == "oh_event"
    assert emitted_data == data
    assert emitted_to == ROOM_KEY.format(sid=sid)

    # _wait_websocket_initial_complete should be set to False after the loop
    assert fake_session._wait_websocket_initial_complete is False

    # logger.debug should have captured at least one message about client wait timeout
    assert any("Using client wait timeout" in m for m in logger.debug_msgs)


@pytest.mark.asyncio
async def test_emit_runtime_error_round_044(monkeypatch):
    """If sio.emit raises RuntimeError, _send should catch it, set is_alive to False and return False."""
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    sid = "sid-4"
    sio = DummySio(sid, good_after_calls=1, raise_on_emit=True)

    fake_session = types.SimpleNamespace()
    fake_session.is_alive = True
    fake_session.sid = sid
    fake_session.config = DummyConfig(client_wait_timeout=1)
    logger = DummyLogger()
    fake_session.logger = logger
    fake_session.sio = sio
    fake_session._wait_websocket_initial_complete = False
    fake_session.last_active_ts = None

    result = await WebSession._send(fake_session, {"bad": True})

    assert result is False
    # is_alive must have been set to False in exception handler
    assert fake_session.is_alive is False
    # an error log entry should have been recorded
    assert len(logger.error_msgs) >= 1
