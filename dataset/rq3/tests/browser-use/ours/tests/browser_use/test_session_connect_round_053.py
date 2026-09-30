import asyncio
import types
import pytest

from browser_use.browser import session as session_module


class _FakeLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []
        self.errors = []

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

    def error(self, msg):
        self.errors.append(msg)


async def _noop_async(*_, **__):
    return None


def test_connect_raises_no_cdp_url_round_053():
    """When no CDP URL is available, connect() must raise a clear RuntimeError.

    This exercises the early guard at line 1739.
    """
    # Build a minimal 'self' for binding the method. Only the attributes used
    # before the early raise are provided.
    fake = types.SimpleNamespace()
    fake.browser_profile = types.SimpleNamespace(cdp_url=None, headers=None)
    fake.cdp_url = None
    fake._cdp_client_root = None
    fake.logger = _FakeLogger()

    # Bind the async method to our fake object
    connect_coroutine = session_module.BrowserSession.connect.__get__(fake, object)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(connect_coroutine(None))

    assert "Cannot setup CDP connection without CDP URL" in str(excinfo.value)
    # Ensure no fatal logger calls were emitted in this early failure case
    assert fake.logger.errors == []


def test_connect_creates_target_and_returns_self_round_053(monkeypatch):
    """Successful connect path when using a ws:// CDP URL.

    - Uses a ws:// URL to skip the httpx JSON version fetch branch.
    - Patches TimeoutWrappedCDPClient and SessionManager to deterministic fakes.
    - Verifies that a new target is created (createTarget called) and that
      the session's agent_focus_target_id is set via get_or_create_cdp_session.
    """
    # Prepare a fake TimeoutWrappedCDPClient used by the code under test
    class FakeTargetAPI:
        def __init__(self):
            # Target API methods are async callables
            async def setAutoAttach(params=None):
                # record parameters for debugging if desired
                self._set_params = params
                return None

            async def createTarget(params=None):
                # Simulate CDP returning a dict with a targetId
                return {"targetId": "TID123"}

            self.setAutoAttach = setAutoAttach
            self.createTarget = createTarget

    class FakeSend:
        def __init__(self):
            self.Target = FakeTargetAPI()

    class FakeTimeoutWrappedCDPClient:
        def __init__(self, url, additional_headers=None, max_ws_frame_size=None):
            self.url = url
            self.additional_headers = additional_headers
            self.max_ws_frame_size = max_ws_frame_size
            self.started = False
            self.stopped = False
            self.send = FakeSend()

        async def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

    # Patch the symbol where connect resolves TimeoutWrappedCDPClient
    monkeypatch.setattr(session_module, "TimeoutWrappedCDPClient", FakeTimeoutWrappedCDPClient)

    # Prepare a fake SessionManager. It must implement start_monitoring() and
    # get_all_page_targets() and get_target().
    class FakeSessionManager:
        def __init__(self, session):
            self._session = session
            self.started = False
            self.cleared = False

        async def start_monitoring(self):
            self.started = True

        def get_all_page_targets(self):
            # Return an empty list so code will call createTarget branch
            return []

        def get_target(self, target_id):
            # Return a fake target object with a title
            return types.SimpleNamespace(title="OK", target_id=target_id, url="about:blank")

        async def clear(self):
            self.cleared = True

    monkeypatch.setattr(session_module, "SessionManager", FakeSessionManager)

    # Build the fake 'self' instance with attributes used by connect()
    fake = types.SimpleNamespace()
    fake.browser_profile = types.SimpleNamespace(cdp_url=None, headers=None)
    # Provide a WS URL to bypass the httpx fetch branch
    fake.cdp_url = "ws://localhost:9222"
    fake._cdp_client_root = None
    fake.logger = _FakeLogger()
    fake.session_manager = None
    fake.event_bus = types.SimpleNamespace()
    fake.event_bus.dispatched = []

    def dispatch(ev):
        fake.event_bus.dispatched.append(ev)

    fake.event_bus.dispatch = dispatch

    # Must provide methods that connect() will await or call
    async def fake_get_or_create_cdp_session(target_id, focus=False):
        # Simulate assigning agent_focus_target_id as the real code expects
        fake.agent_focus_target_id = target_id
        # Return a session object with session_id and cdp_client.send.Page.navigate
        async def nav(params=None, session_id=None):
            return {"result": True}

        fake_session = types.SimpleNamespace()
        fake_session.session_id = "sess-1"
        fake_session.cdp_client = types.SimpleNamespace()
        fake_session.cdp_client.send = types.SimpleNamespace()
        fake_session.cdp_client.send.Page = types.SimpleNamespace(navigate=nav)
        return fake_session

    fake.get_or_create_cdp_session = fake_get_or_create_cdp_session

    # _setup_proxy_auth must be awaitable
    fake._setup_proxy_auth = _noop_async
    # _attach_ws_drop_callback is a synchronous attach helper
    fake._attach_ws_drop_callback = lambda: None

    # agent_focus_target_id starts None
    fake.agent_focus_target_id = None

    # Bind the async connect method
    connect_coroutine = session_module.BrowserSession.connect.__get__(fake, object)

    # Execute the coroutine
    result = asyncio.run(connect_coroutine(None))

    # The method should return self
    assert result is fake

    # Verify that the TimeoutWrappedCDPClient was created and started
    # It's stored to fake._cdp_client_root by connect(); ensure fields present
    assert getattr(fake, "_cdp_client_root") is not None
    assert fake._cdp_client_root.started is True

    # Ensure SessionManager was instantiated and its start_monitoring called
    assert fake.session_manager is not None
    assert getattr(fake.session_manager, "started") is True

    # Because there were no initial page targets, connect() created a new one
    # and our fake get_or_create_cdp_session should have set agent_focus_target_id
    assert fake.agent_focus_target_id == "TID123"

    # No TabCreatedEvent should have been dispatched because there were no page targets
    assert fake.event_bus.dispatched == []
