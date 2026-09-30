# file: openhands/server/conversation_manager/standalone_conversation_manager.py:189-238
# asked: {"lines": [190, 191, 192, 194, 195, 196, 197, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 213, 215, 216, 218, 219, 220, 222, 223, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 237, 238], "branches": [[190, 0], [190, 191], [195, 196], [195, 200], [200, 201], [200, 203], [207, 208], [207, 215], [209, 207], [209, 213], [229, 230], [229, 231]]}
# gained: {"lines": [190, 191, 192, 194, 195, 196, 197, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 213, 215, 216, 218, 219, 220, 222, 223, 226, 227, 228, 229, 230, 231, 232, 233, 235], "branches": [[190, 0], [190, 191], [195, 196], [195, 200], [200, 201], [200, 203], [207, 208], [207, 215], [209, 207], [209, 213], [229, 230], [229, 231]]}

import asyncio
import time
import importlib
from types import SimpleNamespace

import pytest

module_path = "openhands.server.conversation_manager.standalone_conversation_manager"
mod = importlib.import_module(module_path)
StandaloneConversationManager = mod.StandaloneConversationManager
AgentState = importlib.import_module("openhands.core.schema.agent").AgentState


class FakeConversation:
    def __init__(self):
        self.disconnected = False

    async def disconnect(self):
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
async def test_cleanup_stale_close_delay_zero(monkeypatch):
    # Setup manager with close_delay = 0 and a detached conversation that should be disconnected then return
    cfg = SimpleNamespace(sandbox=SimpleNamespace(close_delay=0))
    mgr = StandaloneConversationManager(None, cfg, None, None)

    # Put a detached conversation to ensure disconnect is called before early return
    conv = FakeConversation()
    mgr._detached_conversations["s1"] = (conv, time.time())

    # Ensure should_continue returns True at least once
    calls = {"n": 0}

    def fake_should_continue():
        calls["n"] += 1
        return True

    monkeypatch.setattr(mod, "should_continue", fake_should_continue)

    # Run cleanup
    await mgr._cleanup_stale()

    # Postconditions: conversation disconnected and removed
    assert conv.disconnected is True
    assert "s1" not in mgr._detached_conversations


@pytest.mark.asyncio
async def test_cleanup_stale_closes_old_sessions(monkeypatch):
    # Setup manager with small close_delay > 0
    close_delay = 1.0
    cfg = SimpleNamespace(sandbox=SimpleNamespace(close_delay=close_delay))
    mgr = StandaloneConversationManager(None, cfg, None, None)

    now = time.time()
    # old session: last active older than close_delay, state not RUNNING or None
    old_sid = "old"
    old_session = FakeSession(now - (close_delay + 10), AgentState.STOPPED)
    # recent session: should not be closed
    recent_sid = "recent"
    recent_session = FakeSession(now, AgentState.STOPPED)

    mgr._local_agent_loops_by_sid = {old_sid: old_session, recent_sid: recent_session}

    # get_connections returns empty -> no connected sids
    async def fake_get_connections(filter_to_sids=None, user_id=None):
        return {}

    monkeypatch.setattr(mgr, "get_connections", fake_get_connections)

    closed = []

    async def fake_close_session(sid):
        closed.append(sid)

    mgr._close_session = fake_close_session

    # Patch wait_all to run provided coroutines
    async def fake_wait_all(gen, timeout=None):
        tasks = [t for t in gen]
        if tasks:
            await asyncio.gather(*tasks)
        return None

    monkeypatch.setattr(mod, "wait_all", fake_wait_all)

    # Patch should_continue to run one iteration then stop
    seq = {"n": 0}

    def fake_should_continue():
        seq["n"] += 1
        return seq["n"] == 1

    monkeypatch.setattr(mod, "should_continue", fake_should_continue)

    # Patch asyncio.sleep used inside module to avoid real sleep
    async def fake_sleep(sec):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    # Run cleanup
    await mgr._cleanup_stale()

    # Assert that only the old session was closed
    assert old_sid in closed
    assert recent_sid not in closed


@pytest.mark.asyncio
async def test_cleanup_stale_on_cancelled(monkeypatch):
    # Setup manager
    cfg = SimpleNamespace(sandbox=SimpleNamespace(close_delay=10.0))
    mgr = StandaloneConversationManager(None, cfg, None, None)

    # Conversation whose first disconnect raises CancelledError, second call marks disconnected
    class ConversationWithCancel:
        def __init__(self):
            self.disconnected = False
            self.calls = 0

        async def disconnect(self):
            self.calls += 1
            if self.calls == 1:
                # Simulate task cancellation occurring during disconnect
                raise asyncio.CancelledError()
            self.disconnected = True

    conv = ConversationWithCancel()
    mgr._detached_conversations = {"d1": (conv, time.time())}

    # Add some running loops to be closed via wait_all
    mgr._local_agent_loops_by_sid = {
        "s1": FakeSession(time.time(), AgentState.STOPPED),
        "s2": FakeSession(time.time(), AgentState.STOPPED),
    }

    closed = []

    async def fake_close_session(sid):
        closed.append(sid)

    mgr._close_session = fake_close_session

    # Patch wait_all to run provided coroutines
    async def fake_wait_all(gen, timeout=None):
        tasks = [t for t in gen]
        if tasks:
            await asyncio.gather(*tasks)
        return None

    monkeypatch.setattr(mod, "wait_all", fake_wait_all)

    # Ensure should_continue True to enter the loop
    monkeypatch.setattr(mod, "should_continue", lambda: True)

    # Patch asyncio.sleep in module to no-op to avoid delays
    async def fake_sleep(sec):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    # Run cleanup which should encounter CancelledError from first disconnect,
    # then run the except branch where disconnect is called again and sessions closed.
    await mgr._cleanup_stale()

    # After cancellation handling, the conversation should be disconnected and cleared
    assert conv.disconnected is True
    assert mgr._detached_conversations == {}
    # Both sessions should have been closed
    assert set(closed) == {"s1", "s2"}
