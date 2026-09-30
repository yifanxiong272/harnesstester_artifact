import asyncio
import types
import pytest

from types import SimpleNamespace

import openhands.server.conversation_manager.standalone_conversation_manager as scm_module
from openhands.server.conversation_manager.standalone_conversation_manager import (
    StandaloneConversationManager,
)


class DummyServerConversation:
    def __init__(self, sid, file_store=None, config=None, user_id=None, event_stream=None, runtime=None):
        self.sid = sid
        self.file_store = file_store
        self.config = config
        self.user_id = user_id
        self.event_stream = event_stream
        self.runtime = runtime
        self.connected = False
        self.disconnected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.disconnected = True


class RaisingServerConversation(DummyServerConversation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def connect(self):
        # Simulate runtime unavailable error during connect
        raise scm_module.AgentRuntimeUnavailableError("no runtime")


@pytest.mark.asyncio
async def test_attach_to_conversation_session_missing_round_036(monkeypatch):
    """When session_exists returns False, attach_to_conversation should return None."""
    # Patch session_exists to be deterministic and return False
    async def fake_session_exists(sid, file_store, user_id=None):
        return False

    monkeypatch.setattr(scm_module, "session_exists", fake_session_exists)

    # Create a bare instance without running __init__ and set only attributes needed
    inst = object.__new__(StandaloneConversationManager)
    inst.file_store = object()
    inst.config = object()
    inst._conversations_lock = asyncio.Lock()
    inst._active_conversations = {}
    inst._detached_conversations = {}
    inst._local_agent_loops_by_sid = {}

    result = await inst.attach_to_conversation("missing_sid", user_id="user1")
    assert result is None


@pytest.mark.asyncio
async def test_reuse_active_and_detached_conversation_round_036(monkeypatch):
    """When a conversation is in _active_conversations it should be reused and count incremented.
    When present in _detached_conversations it should be moved to _active_conversations with count 1.
    """
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm_module, "session_exists", fake_session_exists)

    inst = object.__new__(StandaloneConversationManager)
    inst.file_store = object()
    inst.config = object()
    inst._conversations_lock = asyncio.Lock()
    inst._active_conversations = {}
    inst._detached_conversations = {}
    inst._local_agent_loops_by_sid = {}

    # Reuse active conversation
    active_conv = DummyServerConversation("sid-active")
    inst._active_conversations["sid-active"] = (active_conv, 2)

    res = await inst.attach_to_conversation("sid-active", user_id=None)
    # Should return same object and increment count
    assert res is active_conv
    assert inst._active_conversations["sid-active"][1] == 3

    # Detached conversation reuse
    detached_conv = DummyServerConversation("sid-detached")
    inst._active_conversations.clear()
    inst._detached_conversations["sid-detached"] = (detached_conv, 999)

    res2 = await inst.attach_to_conversation("sid-detached", user_id=None)
    assert res2 is detached_conv
    # Should have moved into active_conversations with count 1
    assert "sid-detached" in inst._active_conversations
    assert inst._active_conversations["sid-detached"][1] == 1


@pytest.mark.asyncio
async def test_create_new_conversation_with_session_runtime_round_036(monkeypatch):
    """If no active/detached conversation exists and a local agent loop provides an event_stream/runtime,
    attach_to_conversation should create a ServerConversation using those values and register it active.
    """
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm_module, "session_exists", fake_session_exists)

    # Patch ServerConversation to our dummy that captures constructor args and has a successful connect
    monkeypatch.setattr(scm_module, "ServerConversation", DummyServerConversation)

    inst = object.__new__(StandaloneConversationManager)
    inst.file_store = "FS"
    inst.config = {"cfg": True}
    inst._conversations_lock = asyncio.Lock()
    inst._active_conversations = {}
    inst._detached_conversations = {}

    # Create a fake agent loop info with an agent_session providing event_stream and runtime
    fake_agent_session = SimpleNamespace(event_stream="EVS", runtime="RT")
    fake_loop_info = SimpleNamespace(agent_session=fake_agent_session)
    inst._local_agent_loops_by_sid = {"s_with_runtime": fake_loop_info}

    conv = await inst.attach_to_conversation("s_with_runtime", user_id="u123")

    # Should have produced our DummyServerConversation and connected it
    assert isinstance(conv, DummyServerConversation)
    assert conv.event_stream == "EVS"
    assert conv.runtime == "RT"
    # It must be recorded in active_conversations with count 1
    assert inst._active_conversations["s_with_runtime"][0] is conv
    assert inst._active_conversations["s_with_runtime"][1] == 1


@pytest.mark.asyncio
async def test_connect_raises_agent_runtime_unavailable_round_036(monkeypatch):
    """If ServerConversation.connect raises AgentRuntimeUnavailableError, attach_to_conversation should
    disconnect the conversation and return None."""
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm_module, "session_exists", fake_session_exists)
    # Patch ServerConversation to one that raises on connect
    monkeypatch.setattr(scm_module, "ServerConversation", RaisingServerConversation)

    inst = object.__new__(StandaloneConversationManager)
    inst.file_store = "FS"
    inst.config = {}
    inst._conversations_lock = asyncio.Lock()
    inst._active_conversations = {}
    inst._detached_conversations = {}
    inst._local_agent_loops_by_sid = {}

    res = await inst.attach_to_conversation("sid-error", user_id=None)
    assert res is None
