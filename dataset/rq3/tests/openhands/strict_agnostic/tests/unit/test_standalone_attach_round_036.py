import importlib
import asyncio
import pytest

# Import the module under test
scm = importlib.import_module("openhands.server.conversation_manager.standalone_conversation_manager")

# Helpers used in tests
class _SimpleAgentSession:
    def __init__(self, event_stream=None, runtime=None):
        self.event_stream = event_stream
        self.runtime = runtime

class _LocalSessionHolder:
    def __init__(self, agent_session):
        self.agent_session = agent_session

class FakeConvSuccess:
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
        # simulate small delay but deterministic
        await asyncio.sleep(0)
        self.connected = True

    async def disconnect(self):
        self.disconnected = True

class FakeConvRaise:
    def __init__(self, sid, file_store=None, config=None, user_id=None, event_stream=None, runtime=None):
        self.sid = sid
        self.disconnected = False

    async def connect(self):
        await asyncio.sleep(0)
        # Raise the module-level AgentRuntimeUnavailableError to hit the except branch
        raise scm.AgentRuntimeUnavailableError("fake-unavailable")

    async def disconnect(self):
        self.disconnected = True


@pytest.mark.asyncio
async def test_session_missing_round_036(monkeypatch):
    """If session_exists returns False, attach_to_conversation returns None."""
    # Arrange
    async def _session_exists_false(sid, file_store, user_id=None):
        return False

    monkeypatch.setattr(scm, "session_exists", _session_exists_false)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    # Act
    res = await mgr.attach_to_conversation("session-missing", user_id=None)

    # Assert
    assert res is None


@pytest.mark.asyncio
async def test_reuse_active_round_036(monkeypatch):
    """If sid is in _active_conversations we reuse and increment count."""
    async def _session_exists_true(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", _session_exists_true)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    existing_conv = object()
    mgr._active_conversations = {"sid-active": (existing_conv, 1)}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    res = await mgr.attach_to_conversation("sid-active")

    assert res is existing_conv
    # Count should have incremented from 1 to 2
    assert mgr._active_conversations["sid-active"][1] == 2


@pytest.mark.asyncio
async def test_reuse_detached_round_036(monkeypatch):
    """If sid is in _detached_conversations we pop and promote to active."""
    async def _session_exists_true(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", _session_exists_true)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    detached_conv = object()
    mgr._active_conversations = {}
    mgr._detached_conversations = {"sid-detached": (detached_conv, "meta")}
    mgr._local_agent_loops_by_sid = {}

    res = await mgr.attach_to_conversation("sid-detached")

    assert res is detached_conv
    # Should be in active with initial count 1
    assert "sid-detached" in mgr._active_conversations
    assert mgr._active_conversations["sid-detached"][1] == 1
    # Detached should be removed
    assert "sid-detached" not in mgr._detached_conversations


@pytest.mark.asyncio
async def test_create_with_session_event_stream_round_036(monkeypatch):
    """When a local agent loop exists, its event_stream/runtime should be passed to ServerConversation."""
    async def _session_exists_true(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", _session_exists_true)
    # Replace ServerConversation with our fake that records event_stream/runtime
    monkeypatch.setattr(scm, "ServerConversation", FakeConvSuccess)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = "file-store-x"
    mgr.config = {"cfg": True}
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}

    # Create a fake local session that has an agent_session with event_stream and runtime
    agent_session = _SimpleAgentSession(event_stream="EVT", runtime="RT")
    mgr._local_agent_loops_by_sid = {"sid-local": _LocalSessionHolder(agent_session)}

    res = await mgr.attach_to_conversation("sid-local", user_id="user-1")

    # Should return our FakeConvSuccess instance and it should be connected and recorded in active
    assert isinstance(res, FakeConvSuccess)
    assert res.connected is True
    assert res.event_stream == "EVT"
    assert res.runtime == "RT"
    assert mgr._active_conversations["sid-local"][0] is res
    assert mgr._active_conversations["sid-local"][1] == 1


@pytest.mark.asyncio
async def test_connect_unavailable_round_036(monkeypatch):
    """If ServerConversation.connect raises AgentRuntimeUnavailableError we disconnect and return None."""
    async def _session_exists_true(sid, file_store, user_id=None):
        return True

    monkeypatch.setattr(scm, "session_exists", _session_exists_true)

    # Ensure the module's AgentRuntimeUnavailableError is a predictable exception we control
    class _FakeUnavailableError(Exception):
        pass

    monkeypatch.setattr(scm, "AgentRuntimeUnavailableError", _FakeUnavailableError)
    # Replace ServerConversation with the one that raises
    monkeypatch.setattr(scm, "ServerConversation", FakeConvRaise)

    mgr = object.__new__(scm.StandaloneConversationManager)
    mgr.file_store = None
    mgr.config = None
    mgr._conversations_lock = asyncio.Lock()
    mgr._active_conversations = {}
    mgr._detached_conversations = {}
    mgr._local_agent_loops_by_sid = {}

    res = await mgr.attach_to_conversation("sid-raise")

    # When connect fails, attach_to_conversation returns None and nothing is left in active_conversations
    assert res is None
    assert "sid-raise" not in mgr._active_conversations
