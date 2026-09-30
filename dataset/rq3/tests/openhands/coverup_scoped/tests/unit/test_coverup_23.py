# file: openhands/server/conversation_manager/standalone_conversation_manager.py:101-159
# asked: {"lines": [104, 105, 106, 108, 110, 111, 112, 113, 114, 116, 119, 120, 121, 122, 123, 125, 128, 129, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 158, 159], "branches": [[105, 106], [105, 108], [110, 111], [110, 119], [119, 120], [119, 128], [131, 132], [131, 136]]}
# gained: {"lines": [104, 105, 106, 108, 110, 111, 112, 113, 114, 116, 119, 120, 121, 122, 123, 125, 128, 129, 130, 131, 132, 133, 136, 137, 138, 139, 140, 141, 142, 144, 145, 146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 158, 159], "branches": [[105, 106], [105, 108], [110, 111], [110, 119], [119, 120], [119, 128], [131, 132], [131, 136]]}

import asyncio
import importlib
import time

import pytest

from openhands.core.exceptions import AgentRuntimeUnavailableError


MODULE_PATH = "openhands.server.conversation_manager.standalone_conversation_manager"


@pytest.fixture(autouse=True)
def reload_module():
    # Ensure a fresh module state for each test to avoid cross-test pollution
    importlib.reload(importlib.import_module(MODULE_PATH))
    yield
    importlib.reload(importlib.import_module(MODULE_PATH))


@pytest.mark.asyncio
async def test_attach_returns_none_when_session_missing(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    # session_exists -> False
    async def fake_session_exists(sid, file_store, user_id=None):
        assert sid == "missing_sid"
        return False

    monkeypatch.setattr(mod, "session_exists", fake_session_exists)

    mgr = mod.StandaloneConversationManager(sio=None, config=None, file_store=None, server_config=None)

    res = await mgr.attach_to_conversation("missing_sid", user_id="u1")
    assert res is None
    # no active conversations should be present
    assert mgr._active_conversations == {}


@pytest.mark.asyncio
async def test_attach_reuses_active_conversation_and_increments_count(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)

    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(mod, "session_exists", fake_session_exists)

    class DummyConv:
        def __init__(self, sid):
            self.sid = sid

    mgr = mod.StandaloneConversationManager(sio=None, config=None, file_store=None, server_config=None)
    # prepopulate active conversation with count 2
    conv = DummyConv("active_sid")
    mgr._active_conversations["active_sid"] = (conv, 2)

    res = await mgr.attach_to_conversation("active_sid", user_id=None)
    assert res is conv
    # count incremented
    assert mgr._active_conversations["active_sid"][1] == 3


@pytest.mark.asyncio
async def test_attach_reuses_detached_conversation(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)

    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(mod, "session_exists", fake_session_exists)

    class DummyConv:
        def __init__(self, sid):
            self.sid = sid

    mgr = mod.StandaloneConversationManager(sio=None, config=None, file_store=None, server_config=None)
    conv = DummyConv("detached_sid")
    # put into detached with some timestamp
    mgr._detached_conversations["detached_sid"] = (conv, time.time())

    res = await mgr.attach_to_conversation("detached_sid", user_id=None)
    assert res is conv
    # moved to active with count 1
    assert "detached_sid" in mgr._active_conversations
    assert mgr._active_conversations["detached_sid"][0] is conv
    assert mgr._active_conversations["detached_sid"][1] == 1
    # removed from detached
    assert "detached_sid" not in mgr._detached_conversations


@pytest.mark.asyncio
async def test_attach_creates_new_conversation_and_connects(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)

    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(mod, "session_exists", fake_session_exists)

    # Create a fake session with agent_session having event_stream and runtime
    class FakeAgentSession:
        def __init__(self):
            self.event_stream = "event-stream-obj"
            self.runtime = "runtime-obj"

    class FakeSession:
        def __init__(self):
            self.agent_session = FakeAgentSession()

    # Dummy ServerConversation replacement to capture constructor args and track connect/disconnect calls
    connect_called = {}
    disconnect_called = {}

    class DummyServerConversation:
        def __init__(self, sid, file_store, config, user_id, event_stream, runtime):
            self.sid = sid
            self.file_store = file_store
            self.config = config
            self.user_id = user_id
            self.event_stream = event_stream
            self.runtime = runtime
            connect_called[sid] = False
            disconnect_called[sid] = False

        async def connect(self):
            connect_called[self.sid] = True
            # succeed

        async def disconnect(self):
            disconnect_called[self.sid] = True

    monkeypatch.setattr(mod, "ServerConversation", DummyServerConversation)

    mgr = mod.StandaloneConversationManager(sio=None, config="cfg", file_store="fs", server_config=None)
    # add a local session so event_stream and runtime are used
    mgr._local_agent_loops_by_sid["new_sid"] = FakeSession()

    res = await mgr.attach_to_conversation("new_sid", user_id="user-x")
    assert isinstance(res, DummyServerConversation)
    # connect called
    assert connect_called.get("new_sid", False) is True
    # active conversations contains the new conversation with count 1
    assert "new_sid" in mgr._active_conversations
    conv, count = mgr._active_conversations["new_sid"]
    assert conv is res
    assert count == 1
    # ensure event_stream and runtime were passed through
    assert res.event_stream == "event-stream-obj"
    assert res.runtime == "runtime-obj"


@pytest.mark.asyncio
async def test_attach_handles_agent_runtime_unavailable(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)

    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(mod, "session_exists", fake_session_exists)

    disconnect_called = {}

    class FailingServerConversation:
        def __init__(self, sid, file_store, config, user_id, event_stream, runtime):
            self.sid = sid
            disconnect_called[sid] = False

        async def connect(self):
            raise AgentRuntimeUnavailableError("no runtime")

        async def disconnect(self):
            disconnect_called[self.sid] = True

    monkeypatch.setattr(mod, "ServerConversation", FailingServerConversation)

    mgr = mod.StandaloneConversationManager(sio=None, config=None, file_store=None, server_config=None)

    res = await mgr.attach_to_conversation("fail_sid", user_id=None)
    # should return None on runtime unavailable and disconnect called
    assert res is None
    assert disconnect_called.get("fail_sid", False) is True
