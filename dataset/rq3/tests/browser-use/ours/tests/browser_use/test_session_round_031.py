import asyncio
from types import SimpleNamespace
import pytest

from browser_use.browser import session as session_mod

# Bind the real handler from the BrowserSession class to a minimal test object
_on_start = session_mod.BrowserSession.on_BrowserStartEvent

class Dummy:
    pass

Dummy.on_BrowserStartEvent = _on_start

class _Logger:
    def __init__(self):
        self.infos = []
        self.warns = []
        self.debugs = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warns.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

@pytest.mark.asyncio
async def test_cloud_create_browser_success_round_031(monkeypatch):
    """Exercise the cloud-creation branch and ensure returned cdp_url + demo injection paths run."""
    inst = Dummy()

    async def attach_all_watchdogs():
        return None
    inst.attach_all_watchdogs = attach_all_watchdogs

    inst.cdp_url = None

    profile = SimpleNamespace()
    profile.use_cloud = True
    profile.cloud_browser_params = object()
    profile.cdp_url = None
    profile.is_local = True
    profile.demo_mode = True
    inst.browser_profile = profile

    async def create_browser(params):
        return SimpleNamespace(cdpUrl='ws://cloud.example')
    inst._cloud_browser_client = SimpleNamespace(create_browser=create_browser)

    inst.logger = _Logger()

    dispatched = {}
    async def dispatch(event):
        dispatched['event'] = event
        return None
    inst.event_bus = SimpleNamespace(dispatch=dispatch)

    inst._connection_lock = asyncio.Lock()
    inst._cdp_client_root = None

    async def connect(cdp_url):
        inst._cdp_client_root = SimpleNamespace()
        # simulate some async work
        await asyncio.sleep(0)
        # set a public cdp_client attribute used later
        inst.cdp_client = object()
    inst.connect = connect

    demo_ready = {}
    class Demo:
        async def ensure_ready(self):
            demo_ready['injected'] = True
    inst.demo_mode = Demo()

    inst.session_manager = SimpleNamespace()

    async def _wait_for(coro, timeout):
        return await coro
    monkeypatch.setattr(session_mod.asyncio, 'wait_for', _wait_for)

    result = await inst.on_BrowserStartEvent(None)

    assert inst.browser_profile.cdp_url == 'ws://cloud.example'
    assert inst.browser_profile.is_local is False
    ev = dispatched.get('event')
    assert hasattr(ev, 'cdp_url') and ev.cdp_url == inst.browser_profile.cdp_url
    assert demo_ready.get('injected', False) is True
    assert result == {'cdp_url': inst.browser_profile.cdp_url}


@pytest.mark.asyncio
async def test_connect_timeout_cleanup_round_031(monkeypatch):
    """Simulate a TimeoutError from asyncio.wait_for and assert cleanup behavior."""
    inst = Dummy()

    async def attach_all_watchdogs():
        return None
    inst.attach_all_watchdogs = attach_all_watchdogs

    inst.cdp_url = 'ws://already.connected'

    inst._connection_lock = asyncio.Lock()

    calls = []
    async def stop():
        calls.append('stopped')
    mock_cdp = SimpleNamespace(stop=stop)

    # Ensure _cdp_client_root is None at start so connect() is called
    inst._cdp_client_root = None

    # connect() will set a partial client and then yield so wait_for can simulate a timeout
    async def connect(cdp_url):
        inst._cdp_client_root = mock_cdp
        # yield to allow the fake wait_for to notice the partial client
        await asyncio.sleep(0.1)
    inst.connect = connect

    async def clear():
        calls.append('cleared')
    inst.session_manager = SimpleNamespace(clear=clear)

    inst.agent_focus_target_id = 'some-id'

    inst.logger = _Logger()

    # event_bus.dispatch in the outer exception handler is used synchronously in the code -> simple callable
    def dispatch(event):
        return None
    inst.event_bus = SimpleNamespace(dispatch=dispatch)

    # Provide minimal browser_profile and is_local so outer except won't raise AttributeError if hit
    inst.browser_profile = SimpleNamespace(demo_mode=False)
    inst.is_local = True

    # Fake wait_for: run the connect coroutine briefly to allow it to set _cdp_client_root, then cancel and raise
    async def fake_wait_for(coro, timeout):
        task = asyncio.create_task(coro)
        # allow the task to run to the first await (connect sets _cdp_client_root then awaits)
        await asyncio.sleep(0)
        # cancel the task to simulate timeout and raise TimeoutError
        task.cancel()
        raise TimeoutError()

    monkeypatch.setattr(session_mod.asyncio, 'wait_for', fake_wait_for)

    with pytest.raises(RuntimeError) as excinfo:
        await inst.on_BrowserStartEvent(None)

    assert 'connect() timed out after 15s' in str(excinfo.value)

    # stop() and clear() should have been invoked as part of cleanup (stop awaited may have run before cancellation)
    # Depending on ordering, stop/clear may or may not be present; ensure at least that cleanup attempted to run
    assert inst._cdp_client_root is None
    assert inst.session_manager is None
    assert inst.agent_focus_target_id is None
