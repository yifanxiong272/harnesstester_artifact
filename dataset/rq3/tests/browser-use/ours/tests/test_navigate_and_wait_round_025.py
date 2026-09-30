import asyncio
import types
import pytest

from browser_use.browser import session as session_mod

# We'll call the unbound function directly to avoid constructing BrowserSession
_navigate_and_wait = session_mod.BrowserSession._navigate_and_wait

class FakeLogger:
    def __init__(self):
        self.debug_messages = []
        self.error_messages = []
        self.warning_messages = []

    def debug(self, msg):
        self.debug_messages.append(str(msg))

    def error(self, msg):
        self.error_messages.append(str(msg))

    def warning(self, msg):
        self.warning_messages.append(str(msg))

class FakeLoop:
    """Simple fake event loop time keeper. Each call to time() advances by dt."""
    def __init__(self, start=1000.0, dt=0.1):
        self._t = float(start)
        self._dt = float(dt)

    def time(self):
        # advance time each call so loops progress predictably
        self._t += self._dt
        return self._t

class FakeTarget:
    def __init__(self, url):
        self.url = url

class FakeCDPPage:
    def __init__(self, navigate_coro):
        # navigate_coro is an async callable that will be invoked by tests via patched wait_for
        self.navigate = navigate_coro

class FakeCDPClientSend:
    def __init__(self, page):
        self.Page = page

class FakeCDPClient:
    def __init__(self, page):
        self.send = FakeCDPClientSend(page)

class FakeCDPSession:
    def __init__(self, session_id='sess', target_id='target1234', lifecycle_events=None, page_navigate_coro=None):
        self.session_id = session_id
        self.target_id = target_id
        if page_navigate_coro is None:
            async def _default(params, session_id):
                return {}
            page_navigate_coro = _default
        self.cdp_client = FakeCDPClient(FakeCDPPage(page_navigate_coro))
        if lifecycle_events is not None:
            # intentionally attach attribute only if provided
            self._lifecycle_events = lifecycle_events

class FakeSelf:
    def __init__(self, cdp_session: FakeCDPSession, target_url: str):
        self._cdp_session_obj = cdp_session
        self.session_manager = types.SimpleNamespace(get_target=lambda tid: FakeTarget(target_url))
        self.logger = FakeLogger()

    async def get_or_create_cdp_session(self, target_id, focus=False):
        # return the provided fake session
        return self._cdp_session_obj


# Helpers to patch module-level asyncio references used inside the function under test
class PatchAsyncioContext:
    def __init__(self, module, *, loop=None, wait_for=None):
        self.module = module
        self.loop = loop
        self.wait_for = wait_for
        self._old_loop = None
        self._old_wait_for = None
        self._old_sleep = None

    def __enter__(self):
        # patch get_event_loop and wait_for and sleep in the target module
        if self.loop is not None:
            self._old_loop = self.module.asyncio.get_event_loop
            self.module.asyncio.get_event_loop = lambda: self.loop
        if self.wait_for is not None:
            self._old_wait_for = self.module.asyncio.wait_for
            self.module.asyncio.wait_for = self.wait_for
        # patch sleep to a no-op to keep tests fast
        self._old_sleep = self.module.asyncio.sleep
        async def _noop_sleep(_):
            return None
        self.module.asyncio.sleep = _noop_sleep
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._old_loop is not None:
            self.module.asyncio.get_event_loop = self._old_loop
        if self._old_wait_for is not None:
            self.module.asyncio.wait_for = self._old_wait_for
        if self._old_sleep is not None:
            self.module.asyncio.sleep = self._old_sleep


@pytest.mark.asyncio
async def test_navigate_timeout_raised_round_025():
    """If Page.navigate() times out, a RuntimeError with nav_timeout and url is raised."""
    # arrange: fake loop that advances time
    fake_loop = FakeLoop(start=100.0, dt=0.05)

    async def fake_wait_for(coro, timeout):
        # simulate wait_for timing out
        raise TimeoutError()

    # cdp page navigate coroutine won't actually be awaited because wait_for raises
    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None))
    fake_self = FakeSelf(fake_cdp, target_url='http://example.com/old')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        with pytest.raises(RuntimeError) as ei:
            await _navigate_and_wait(fake_self, 'http://example.com/new', 'tid', timeout=None, wait_until='load', nav_timeout=None)

    # assert runtime error mentions the default nav_timeout (20.0s) and the requested URL
    assert 'Page.navigate() timed out after 20.0s' in str(ei.value)
    assert 'http://example.com/new' in str(ei.value)


@pytest.mark.asyncio
async def test_navigate_errorText_raises_round_025():
    """If CDP returns an errorText navigation result, raise a RuntimeError with that text."""
    fake_loop = FakeLoop(start=200.0, dt=0.01)

    async def fake_wait_for(coro, timeout):
        # return a dict that signals navigation error
        return {'errorText': 'boom!!'}

    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None))
    fake_self = FakeSelf(fake_cdp, target_url='http://a.com')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        with pytest.raises(RuntimeError) as ei:
            await _navigate_and_wait(fake_self, 'http://a.com/path', 'tid', timeout=None, wait_until='load', nav_timeout=5.0)

    assert 'Navigation failed: boom!!' in str(ei.value)


@pytest.mark.asyncio
async def test_wait_until_commit_returns_round_025():
    """When wait_until == 'commit', function should return early and log a commit-ready message."""
    fake_loop = FakeLoop(start=300.0, dt=0.02)

    async def fake_wait_for(coro, timeout):
        return {'loaderId': 'L1'}

    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None))
    fake_self = FakeSelf(fake_cdp, target_url='http://same.domain')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        # should not raise
        await _navigate_and_wait(fake_self, 'http://same.domain/abc', 'tid', timeout=None, wait_until='commit', nav_timeout=None)

    # verify a debug message recorded includes the word 'commit'
    found = any('commit' in m for m in fake_self.logger.debug_messages)
    assert found, f"Expected commit message in debug logs, got: {fake_self.logger.debug_messages}"


@pytest.mark.asyncio
async def test_lifecycle_monitoring_missing_raises_round_025():
    """If CDP session is missing lifecycle monitoring state, raise a RuntimeError describing it."""
    fake_loop = FakeLoop(start=400.0, dt=0.01)

    async def fake_wait_for(coro, timeout):
        return {'loaderId': None}

    # Create a CDP session without the _lifecycle_events attribute to trigger the error
    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None))
    # explicitly remove attribute if created
    if hasattr(fake_cdp, '_lifecycle_events'):
        delattr(fake_cdp, '_lifecycle_events')
    fake_self = FakeSelf(fake_cdp, target_url='http://z.domain')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        with pytest.raises(RuntimeError) as ei:
            await _navigate_and_wait(fake_self, 'http://z.domain/foo', 'tid', timeout=1.0, wait_until='load', nav_timeout=1.0)

    assert 'Lifecycle monitoring not enabled' in str(ei.value)
    # ensure the target id prefix appears in the message for diagnosability
    assert fake_cdp.target_id[:4] in str(ei.value)


@pytest.mark.asyncio
async def test_lifecycle_event_matching_returns_round_025():
    """If a lifecycle event matching acceptable_events and loaderId is seen, function returns and logs readiness."""
    fake_loop = FakeLoop(start=500.0, dt=0.01)

    async def fake_wait_for(coro, timeout):
        # return a loader id that indicates navigation's loader
        return {'loaderId': 'loader-XYZ'}

    # lifecycle events include a 'load' event that matches navigation loaderId
    lifecycle_events = [
        {'name': 'load', 'loaderId': 'loader-XYZ'},
    ]
    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None), lifecycle_events=lifecycle_events)
    fake_self = FakeSelf(fake_cdp, target_url='http://match.local')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        # pass an explicit timeout so the loop condition will be true initially
        await _navigate_and_wait(fake_self, 'http://match.local/p', 'tid', timeout=5.0, wait_until='load', nav_timeout=2.0)

    # verify that debug log contains the event name
    assert any('load' in m for m in fake_self.logger.debug_messages), fake_self.logger.debug_messages


@pytest.mark.asyncio
async def test_no_events_logs_error_round_025():
    """When lifecycle monitoring yields no seen events before timeout, an error log is emitted."""
    fake_loop = FakeLoop(start=600.0, dt=0.01)

    async def fake_wait_for(coro, timeout):
        return {'loaderId': 'some-loader'}

    # attach an empty lifecycle events list to the session
    fake_cdp = FakeCDPSession(page_navigate_coro=(lambda *a, **k: None), lifecycle_events=[])
    fake_self = FakeSelf(fake_cdp, target_url='http://noevents')

    with PatchAsyncioContext(session_mod, loop=fake_loop, wait_for=fake_wait_for):
        # use timeout=0 to ensure loop body is skipped and seen_events remains empty
        await _navigate_and_wait(fake_self, 'http://noevents/', 'tid', timeout=0, wait_until='load', nav_timeout=1.0)

    # after returning, since no seen_events were recorded we expect an error log
    assert any('No lifecycle events received' in m for m in fake_self.logger.error_messages), fake_self.logger.error_messages
