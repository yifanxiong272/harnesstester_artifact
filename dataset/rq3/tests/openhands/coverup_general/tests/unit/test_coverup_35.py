# file: openhands/server/conversation_manager/standalone_conversation_manager.py:101-159
# asked: {"lines": [104, 105, 106, 108, 110, 111, 112, 113, 114, 116, 119, 120, 121, 122, 123, 125, 128, 129, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 158, 159], "branches": [[105, 106], [105, 108], [110, 111], [110, 119], [119, 120], [119, 128], [131, 132], [131, 136]]}
# gained: {"lines": [104, 105, 106, 108, 110, 111, 112, 113, 114, 116, 119, 120, 121, 122, 123, 125, 128, 129, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 158, 159], "branches": [[105, 106], [105, 108], [110, 111], [110, 119], [119, 120], [119, 128], [131, 132], [131, 136]]}

import asyncio
import time
import pytest

from openhands.core.exceptions import AgentRuntimeUnavailableError
import openhands.server.conversation_manager.standalone_conversation_manager as scm_mod


@pytest.mark.asyncio
async def test_attach_returns_none_when_session_missing(monkeypatch):
    sid = "sid-missing"

    async def fake_session_exists(sid_arg, file_store, user_id=None):
        assert sid_arg == sid
        return False

    monkeypatch.setattr(scm_mod, "session_exists", fake_session_exists)

    manager = scm_mod.StandaloneConversationManager(
        sio=None,
        config=object(),
        file_store=object(),
        server_config=object(),
    )

    res = await manager.attach_to_conversation(sid, user_id="u1")
    assert res is None
    # ensure no active/detached recorded
    assert sid not in manager._active_conversations
    assert sid not in manager._detached_conversations


@pytest.mark.asyncio
async def test_attach_reuses_active_conversation_and_increments_count(monkeypatch):
    sid = "sid-active"

    async def fake_session_exists(sid_arg, file_store, user_id=None):
        assert sid_arg == sid
        return True

    monkeypatch.setattr(scm_mod, "session_exists", fake_session_exists)

    manager = scm_mod.StandaloneConversationManager(
        sio=None,
        config=object(),
        file_store=object(),
        server_config=object(),
    )

    # create a dummy conversation object
    class DummyConversation:
        pass

    conv = DummyConversation()
    manager._active_conversations[sid] = (conv, 2)

    res = await manager.attach_to_conversation(sid, user_id=None)
    assert res is conv
    # count incremented
    assert manager._active_conversations[sid][1] == 3


@pytest.mark.asyncio
async def test_attach_reuses_detached_conversation(monkeypatch):
    sid = "sid-detached"

    async def fake_session_exists(sid_arg, file_store, user_id=None):
        assert sid_arg == sid
        return True

    monkeypatch.setattr(scm_mod, "session_exists", fake_session_exists)

    manager = scm_mod.StandaloneConversationManager(
        sio=None,
        config=object(),
        file_store=object(),
        server_config=object(),
    )

    class DummyConversation:
        pass

    conv = DummyConversation()
    manager._detached_conversations[sid] = (conv, time.time() - 10.0)

    res = await manager.attach_to_conversation(sid, user_id="user-x")
    assert res is conv
    # moved to active with count 1
    assert sid in manager._active_conversations
    assert manager._active_conversations[sid][0] is conv
    assert manager._active_conversations[sid][1] == 1
    # detached removed
    assert sid not in manager._detached_conversations


@pytest.mark.asyncio
async def test_attach_creates_new_conversation_and_connects(monkeypatch):
    sid = "sid-new-connect"

    async def fake_session_exists(sid_arg, file_store, user_id=None):
        assert sid_arg == sid
        return True

    monkeypatch.setattr(scm_mod, "session_exists", fake_session_exists)

    # Fake ServerConversation implementation to be used by the manager
    class FakeServerConversation:
        def __init__(self, sid_arg, file_store, config, user_id, event_stream=None, runtime=None):
            self.sid = sid_arg
            self.file_store = file_store
            self.config = config
            self.user_id = user_id
            self.event_stream = event_stream
            self.runtime = runtime
            self.connected = False
            self.disconnected = False

        async def connect(self):
            # simulate small delay
            await asyncio.sleep(0)
            self.connected = True

        async def disconnect(self):
            await asyncio.sleep(0)
            self.disconnected = True

    monkeypatch.setattr(scm_mod, "ServerConversation", FakeServerConversation)

    manager = scm_mod.StandaloneConversationManager(
        sio=None,
        config={"cfg": True},
        file_store={"fs": True},
        server_config=object(),
    )

    # Simulate an agent session present to exercise event_stream/runtime branch
    class DummyAgentSession:
        def __init__(self):
            class Inner:
                event_stream = "evstream"
                runtime = "runt"
            self.agent_session = Inner()

    manager._local_agent_loops_by_sid[sid] = DummyAgentSession()

    res = await manager.attach_to_conversation(sid, user_id="user-connect")
    assert isinstance(res, FakeServerConversation)
    assert res.sid == sid
    assert res.connected is True
    # check stored in active with count 1
    assert sid in manager._active_conversations
    stored_conv, cnt = manager._active_conversations[sid]
    assert stored_conv is res
    assert cnt == 1
    # event_stream/runtime passed through
    assert res.event_stream == "evstream"
    assert res.runtime == "runt"


@pytest.mark.asyncio
async def test_attach_handles_connect_failure_and_disconnects(monkeypatch):
    sid = "sid-new-fail"

    async def fake_session_exists(sid_arg, file_store, user_id=None):
        assert sid_arg == sid
        return True

    monkeypatch.setattr(scm_mod, "session_exists", fake_session_exists)

    # Fake ServerConversation whose connect raises AgentRuntimeUnavailableError
    class FakeServerConversationFail:
        def __init__(self, sid_arg, file_store, config, user_id, event_stream=None, runtime=None):
            self.sid = sid_arg
            self.disconnected = False

        async def connect(self):
            await asyncio.sleep(0)
            raise AgentRuntimeUnavailableError("no runtime")

        async def disconnect(self):
            self.disconnected = True

    monkeypatch.setattr(scm_mod, "ServerConversation", FakeServerConversationFail)

    manager = scm_mod.StandaloneConversationManager(
        sio=None,
        config=object(),
        file_store=object(),
        server_config=object(),
    )

    res = await manager.attach_to_conversation(sid, user_id=None)
    # should return None on failure
    assert res is None
    # should not be in active conversations
    assert sid not in manager._active_conversations
