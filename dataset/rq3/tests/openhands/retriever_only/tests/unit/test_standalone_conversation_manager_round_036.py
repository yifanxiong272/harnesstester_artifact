import asyncio
import types
import pytest

from openhands.server.conversation_manager import standalone_conversation_manager as scm

# Helper fake ServerConversation classes used to control connect/disconnect behavior
class FakeServerConversationBase:
    def __init__(self, sid, *, file_store=None, config=None, user_id=None, event_stream=None, runtime=None):
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


class FakeServerConversationFail(FakeServerConversationBase):
    async def connect(self):
        # Simulate the runtime being unavailable to hit the exception branch
        raise scm.AgentRuntimeUnavailableError("no runtime")


class FakeServerConversationRecord(FakeServerConversationBase):
    async def connect(self):
        # Successful connect
        self.connected = True


@pytest.mark.asyncio
async def test_attach_to_conversation_session_missing_round_036(monkeypatch):
    """When session_exists is False, attach_to_conversation should return None immediately."""
    async def fake_session_exists(sid, file_store, user_id=None):
        assert sid == "sid-missing"
        # ensure file_store passed through
        assert file_store == "fs"
        return False

    monkeypatch.setattr(scm, "session_exists", fake_session_exists)

    mgr = object.__new__(scm.StandaloneConversationManager)
    # minimal attributes used by attach_to_conversation
    mgr.file_store = "fs"
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    result = await mgr.attach_to_conversation("sid-missing", user_id="u")
    assert result is None


@pytest.mark.asyncio
async def test_attach_to_conversation_reuse_active_round_036(monkeypatch):
    """If sid is present in _active_conversations, it should be reused and count incremented."""
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", fake_session_exists)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    existing_conv = object()
    mgr._active_conversations = {"sid-active": (existing_conv, 2)}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    returned = await mgr.attach_to_conversation("sid-active")
    assert returned is existing_conv
    # count should be incremented to 3
    assert mgr._active_conversations["sid-active"][1] == 3


@pytest.mark.asyncio
async def test_attach_to_conversation_reuse_detached_round_036(monkeypatch):
    """If sid is in _detached_conversations it should be moved to _active_conversations with count 1."""
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", fake_session_exists)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    conv_obj = object()
    mgr._active_conversations = {}
    mgr._detached_conversations = {"sid-detached": (conv_obj, "meta")}
    mgr._local_agent_loops_by_sid = {}

    returned = await mgr.attach_to_conversation("sid-detached")
    assert returned is conv_obj
    # Should be removed from detached
    assert "sid-detached" not in mgr._detached_conversations
    # And added to active with count 1
    assert mgr._active_conversations["sid-detached"][0] is conv_obj
    assert mgr._active_conversations["sid-detached"][1] == 1


@pytest.mark.asyncio
async def test_attach_to_conversation_connect_failure_round_036(monkeypatch):
    """If ServerConversation.connect raises AgentRuntimeUnavailableError, attach_to_conversation should disconnect and return None."""
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", fake_session_exists)

    # Replace ServerConversation in the module with one that fails on connect
    monkeypatch.setattr(scm, "ServerConversation", FakeServerConversationFail)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = "fs"
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    result = await mgr.attach_to_conversation("sid-fail", user_id="u1")
    # Should return None on failure and not leave an active conversation
    assert result is None
    assert "sid-fail" not in mgr._active_conversations


@pytest.mark.asyncio
async def test_attach_to_conversation_create_and_connect_success_with_runtime_round_036(monkeypatch):
    """When a local agent loop session exists, event_stream and runtime are passed into the ServerConversation and it is activated on successful connect."""
    async def fake_session_exists(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", fake_session_exists)

    # Use a recordable ServerConversation to inspect constructor args
    monkeypatch.setattr(scm, "ServerConversation", FakeServerConversationRecord)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = "fs2"
    mgr.config = {"cfg": True}
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}

    # Create a fake agent loop info with nested agent_session attributes
    agent_session = types.SimpleNamespace(event_stream="evt-stream", runtime="runtime-obj")
    fake_loop_info = types.SimpleNamespace(agent_session=agent_session)
    mgr._local_agent_loops_by_sid = {"sid-new": fake_loop_info}

    returned = await mgr.attach_to_conversation("sid-new", user_id="user-x")
    # Should return the FakeServerConversationRecord instance
    assert isinstance(returned, FakeServerConversationRecord)
    # The event_stream and runtime passed to ServerConversation should match those on the session
    assert returned.event_stream == "evt-stream"
    assert returned.runtime == "runtime-obj"
    # Should now be present in active conversations with count 1
    assert mgr._active_conversations["sid-new"][0] is returned
    assert mgr._active_conversations["sid-new"][1] == 1
