import asyncio
import types
import pytest

# import the module under test
import importlib
scm = importlib.import_module("openhands.server.conversation_manager.standalone_conversation_manager")
StandaloneConversationManager = scm.StandaloneConversationManager
AgentRuntimeUnavailableError = scm.AgentRuntimeUnavailableError

# Helpers for creating simple coroutine-returning functions for monkeypatching
def _async_return(value):
    async def _c(*a, **k):
        return value
    return _c

class _FakeSession:
    def __init__(self, event_stream=None, runtime=None):
        class AgentSession:
            pass

        self.agent_session = AgentSession()
        self.agent_session.event_stream = event_stream
        self.agent_session.runtime = runtime


class _FakeServerConversationBase:
    def __init__(self, sid, file_store=None, config=None, user_id=None, event_stream=None, runtime=None):
        # record values so tests can assert
        self.sid = sid
        self.file_store = file_store
        self.config = config
        self.user_id = user_id
        self.event_stream = event_stream
        self.runtime = runtime
        self.disconnect_called = False

    async def connect(self):
        # default: succeed
        return None

    async def disconnect(self):
        self.disconnect_called = True


def _make_manager():
    # create instance without calling original __init__
    m = object.__new__(StandaloneConversationManager)
    # minimal attributes used by attach_to_conversation
    m.file_store = "file_store_placeholder"
    m.config = "config_placeholder"
    m._conversations_lock = asyncio.Lock()
    m._active_conversations = {}
    m._detached_conversations = {}
    m._local_agent_loops_by_sid = {}
    return m


def test_attach_returns_none_when_session_missing_round_036(monkeypatch):
    # session_exists -> False should cause early return None
    monkeypatch.setattr(scm, "session_exists", _async_return(False))

    manager = _make_manager()

    result = asyncio.run(manager.attach_to_conversation("missing_sid", user_id=None))
    assert result is None


def test_attach_reuses_active_conversation_and_increments_count_round_036(monkeypatch):
    # session_exists True, sid in _active_conversations -> should return existing conversation and increment count
    monkeypatch.setattr(scm, "session_exists", _async_return(True))

    manager = _make_manager()
    existing_conv = object()
    manager._active_conversations["sid_active"] = (existing_conv, 1)

    result = asyncio.run(manager.attach_to_conversation("sid_active", user_id="u1"))
    assert result is existing_conv
    # ensure count incremented
    assert manager._active_conversations["sid_active"][1] == 2


def test_attach_reuses_detached_conversation_round_036(monkeypatch):
    # session_exists True, sid in _detached_conversations -> should pop and move to active with count 1
    monkeypatch.setattr(scm, "session_exists", _async_return(True))

    manager = _make_manager()
    detached_conv = object()
    manager._detached_conversations["sid_detached"] = (detached_conv, None)

    result = asyncio.run(manager.attach_to_conversation("sid_detached", user_id="u2"))
    assert result is detached_conv
    assert "sid_detached" in manager._active_conversations
    assert manager._active_conversations["sid_detached"][1] == 1


def test_attach_creates_new_conversation_with_session_event_stream_and_runtime_round_036(monkeypatch):
    # session_exists True and there's an agent loop session providing event_stream/runtime
    monkeypatch.setattr(scm, "session_exists", _async_return(True))

    # Create a fake ServerConversation that records init args
    created_instances = []

    class FakeServerConversation(_FakeServerConversationBase):
        async def connect(self):
            # simulate successful connect
            created_instances.append(self)
            return None

    monkeypatch.setattr(scm, "ServerConversation", FakeServerConversation)

    manager = _make_manager()
    # put a fake agent loop session with event_stream and runtime
    manager._local_agent_loops_by_sid["sid_new"] = _FakeSession(event_stream="evstream", runtime="runtimex")

    result = asyncio.run(manager.attach_to_conversation("sid_new", user_id="u3"))
    # should return the created FakeServerConversation instance
    assert isinstance(result, FakeServerConversation)
    # verify that the created instance saw the event_stream and runtime from session
    assert created_instances, "No ServerConversation instances were created"
    inst = created_instances[0]
    assert inst.event_stream == "evstream"
    assert inst.runtime == "runtimex"
    # active conversations should contain the new conversation with count 1
    assert manager._active_conversations["sid_new"][0] is inst
    assert manager._active_conversations["sid_new"][1] == 1


def test_attach_handles_agent_runtime_unavailable_during_connect_round_036(monkeypatch):
    # session_exists True, but ServerConversation.connect raises AgentRuntimeUnavailableError
    monkeypatch.setattr(scm, "session_exists", _async_return(True))

    class FakeBadServerConversation(_FakeServerConversationBase):
        async def connect(self):
            raise AgentRuntimeUnavailableError("no runtime")

        async def disconnect(self):
            # mark disconnect_called via attribute on self
            self.disconnect_called = True

    monkeypatch.setattr(scm, "ServerConversation", FakeBadServerConversation)

    manager = _make_manager()

    result = asyncio.run(manager.attach_to_conversation("sid_bad", user_id="u4"))
    # should return None on runtime unavailable
    assert result is None

    # ensure no active conversation was left behind
    assert "sid_bad" not in manager._active_conversations
