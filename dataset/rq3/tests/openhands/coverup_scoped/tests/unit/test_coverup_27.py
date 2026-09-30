# file: openhands/server/conversation_manager/standalone_conversation_manager.py:189-238
# asked: {"lines": [190, 191, 192, 194, 195, 196, 197, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 213, 215, 216, 218, 219, 220, 222, 223, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 237, 238], "branches": [[190, 0], [190, 191], [195, 196], [195, 200], [200, 201], [200, 203], [207, 208], [207, 215], [209, 207], [209, 213], [229, 230], [229, 231]]}
# gained: {"lines": [190, 191, 192, 194, 195, 196, 197, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 213, 215, 216, 218, 219, 220, 222, 223, 226, 227, 228, 229, 231, 232, 233, 235], "branches": [[190, 0], [190, 191], [195, 196], [195, 200], [200, 201], [200, 203], [207, 208], [207, 215], [209, 207], [209, 213], [229, 231]]}

import asyncio
import time
from types import SimpleNamespace

import pytest

from openhands.core.schema.agent import AgentState
from openhands.server.conversation_manager.standalone_conversation_manager import (
    StandaloneConversationManager,
    _CLEANUP_INTERVAL,
)
from openhands.server.session.agent_session import WAIT_TIME_BEFORE_CLOSE


class FakeConversation:
    def __init__(self):
        self.disconnected = False

    async def disconnect(self):
        # small await to simulate async work
        await asyncio.sleep(0)
        self.disconnected = True


class FakeAgentSession:
    def __init__(self, state):
        self._state = state

    def get_state(self):
        return self._state


class FakeSession:
    def __init__(self, last_active_ts, state):
        self.last_active_ts = last_active_ts
        self.agent_session = FakeAgentSession(state)


@pytest.mark.asyncio
async def test_cleanup_stale_detached_and_close_delay_zero(monkeypatch):
    # Prepare manager with one detached conversation
    config = SimpleNamespace(sandbox=SimpleNamespace(close_delay=0))
    manager = StandaloneConversationManager(sio=object(), config=config, file_store=object(), server_config=object())

    conv = FakeConversation()
    manager._detached_conversations["sid-1"] = (conv, time.time())

    # Ensure should_continue returns True so the loop runs once and then exit via return
    monkeypatch.setattr(
        "openhands.server.conversation_manager.standalone_conversation_manager.should_continue",
        lambda: True,
    )

    # Run cleanup; it should disconnect conv and then return because close_delay is falsy (0)
    await manager._cleanup_stale()

    assert conv.disconnected is True
    # _detached_conversations should have been popped
    assert "sid-1" not in manager._detached_conversations


@pytest.mark.asyncio
async def test_cleanup_stale_close_sessions(monkeypatch):
    # Prepare manager where close_delay > 0 and a running loop is stale and should be closed
    config = SimpleNamespace(sandbox=SimpleNamespace(close_delay=1.0))
    manager = StandaloneConversationManager(sio=object(), config=config, file_store=object(), server_config=object())

    # Make should_continue return True only once so loop runs a single iteration
    state = {"count": 0}

    def sc():
        state["count"] += 1
        return state["count"] == 1

    monkeypatch.setattr(
        "openhands.server.conversation_manager.standalone_conversation_manager.should_continue",
        sc,
    )

    # Place a session that is older than close_threshold and is not RUNNING/None
    old_ts = time.time() - 10.0
    manager._local_agent_loops_by_sid["old-sid"] = FakeSession(last_active_ts=old_ts, state=AgentState.STOPPED)
    # Another session that is recent and should not be closed
    manager._local_agent_loops_by_sid["recent-sid"] = FakeSession(last_active_ts=time.time(), state=AgentState.STOPPED)

    closed = []

    async def fake_close_session(sid):
        await asyncio.sleep(0)
        closed.append(sid)

    # Patch instance method
    monkeypatch.setattr(manager, "_close_session", fake_close_session)

    # Ensure get_connections returns empty mapping so old-sid is not considered connected
    async def fake_get_connections(user_id=None, filter_to_sids=None):
        # return empty mapping
        return {}

    monkeypatch.setattr(manager, "get_connections", fake_get_connections)

    # Also make sleep short to avoid delays even though should_continue will stop loop
    monkeypatch.setattr("openhands.server.conversation_manager.standalone_conversation_manager._CLEANUP_INTERVAL", 0.0)

    await manager._cleanup_stale()

    # old-sid should have been closed via our fake_close_session
    assert "old-sid" in closed
    # recent-sid should not be closed
    assert "recent-sid" not in closed


@pytest.mark.asyncio
async def test_cleanup_stale_cancelled_error_branch(monkeypatch):
    # Prepare manager with detached conversations and local agent loops
    config = SimpleNamespace(sandbox=SimpleNamespace(close_delay=1.0))
    manager = StandaloneConversationManager(sio=object(), config=config, file_store=object(), server_config=object())

    conv = FakeConversation()
    manager._detached_conversations["d1"] = (conv, time.time())

    # local agent loops keys that should be passed to _close_session in except block
    manager._local_agent_loops_by_sid["a1"] = FakeSession(last_active_ts=time.time(), state=AgentState.STOPPED)
    manager._local_agent_loops_by_sid["a2"] = FakeSession(last_active_ts=time.time(), state=AgentState.STOPPED)

    # should_continue True so try block runs
    monkeypatch.setattr(
        "openhands.server.conversation_manager.standalone_conversation_manager.should_continue",
        lambda: True,
    )

    # Cause get_connections to raise CancelledError when awaited
    async def raising_get_connections(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(manager, "get_connections", raising_get_connections)

    closed = []

    async def fake_close_session(sid):
        await asyncio.sleep(0)
        closed.append(sid)

    monkeypatch.setattr(manager, "_close_session", fake_close_session)

    # Monkeypatch wait_all used in the module to simply await each coroutine
    async def fake_wait_all(coros, timeout=None):
        # coros may be a generator; consume and await each
        for c in coros:
            await c
        return None

    monkeypatch.setattr(
        "openhands.server.conversation_manager.standalone_conversation_manager.wait_all",
        fake_wait_all,
    )

    # Run cleanup; get_connections will raise CancelledError and the except block should run
    await manager._cleanup_stale()

    # The detached conversation should have been disconnected and cleared
    assert conv.disconnected is True
    assert manager._detached_conversations == {}

    # _close_session should have been called for both local agent loop sids
    assert set(closed) == {"a1", "a2"}
