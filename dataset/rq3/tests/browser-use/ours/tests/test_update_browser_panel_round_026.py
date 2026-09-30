import types
import builtins
import pytest

import browser_use.cli as cli


class DummyRichLog:
    def __init__(self):
        self.writes = []
        self.cleared = False

    def clear(self):
        self.cleared = True

    def write(self, msg):
        # store normalized messages for deterministic asserts
        self.writes.append(msg)


class FakeViewport:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class FakeBrowserProfile:
    def __init__(self, headless=False, executable_path=None, viewport=None):
        self.headless = headless
        self.executable_path = executable_path
        self.viewport = viewport


class FakeSessionManager:
    def __init__(self, target):
        self._target = target

    def get_focused_target(self):
        return self._target


class FakeTarget:
    def __init__(self, url):
        self.url = url


class FakeBrowserSession:
    def __init__(self, *, cdp_client=None, cdp_url=None, browser_profile=None, agent_focus_target_id=False, session_manager=None):
        self.cdp_client = cdp_client
        self.cdp_url = cdp_url
        self.browser_profile = browser_profile or FakeBrowserProfile()
        self.agent_focus_target_id = agent_focus_target_id
        self.session_manager = session_manager


class DummySelf:
    def __init__(self, browser_session=None, agent=None):
        # attribute expected by the method
        self.browser_session = browser_session
        self.agent = agent
        # query_one should return an object with clear() and write()
        self._last_log = DummyRichLog()

    def query_one(self, selector, rich_log_cls=None):
        # ignore selector/class; always return the same DummyRichLog
        return self._last_log


# Test 1: No browser session -> writes "Browser not initialized"
def test_update_browser_panel_no_session_round_026(monkeypatch):
    dummy = DummySelf(browser_session=None, agent=None)

    # ensure deterministic time (not used here but patching to be safe)
    monkeypatch.setattr(cli.time, 'time', lambda: 1)
    monkeypatch.setattr(cli.time, 'strftime', lambda fmt, t: '00:00:00')

    # Call the unbound function with our dummy self
    cli.BrowserUseApp.update_browser_panel(dummy)

    # Inspect the dummy RichLog
    writes = dummy._last_log.writes
    assert dummy._last_log.cleared is True
    # Expect a single message indicating browser not initialized
    assert any('[red]Browser not initialized' in w for w in writes), f'got: {writes}'


# Test 2: Browser session exists but no cdp_client attribute or cdp_client is None -> waiting message and early return
def test_update_browser_panel_waiting_for_browser_round_026(monkeypatch):
    profile = FakeBrowserProfile(headless=False)
    bs = FakeBrowserSession(cdp_client=None, cdp_url=None, browser_profile=profile)
    dummy = DummySelf(browser_session=bs, agent=None)

    # deterministic time
    monkeypatch.setattr(cli.time, 'time', lambda: 1)
    monkeypatch.setattr(cli.time, 'strftime', lambda fmt, t: '00:00:00')

    cli.BrowserUseApp.update_browser_panel(dummy)

    writes = dummy._last_log.writes
    # Should have the waiting message and return early (so not many subsequent writes)
    assert any('waiting for browser to launch' in w for w in writes), f'got: {writes}'
    # ensure it did not attempt to write PID/Connected info
    assert not any('PID:' in w for w in writes)


# Test 3: Connected CDP session with agent present, viewport set, and focused target -> writes all details including Window and Last updated and focused URL
def test_update_browser_panel_connected_agent_with_focus_and_window_round_026(monkeypatch):
    # Build a viewport and profile indicating headless True so rendering includes headless marker
    viewport = FakeViewport(width=1280, height=720)
    profile = FakeBrowserProfile(headless=True, executable_path=None, viewport=viewport)

    # Target URL longer than 36 chars to trigger truncation and ellipsis
    target = FakeTarget(url='https://www.example.com/some/very/long/path/page.html')
    session_manager = FakeSessionManager(target)

    # cdp_client present -> connected path
    bs = FakeBrowserSession(cdp_client=object(), cdp_url='ws://cdp:9222', browser_profile=profile, agent_focus_target_id=True, session_manager=session_manager)

    # Make an agent object with browser_session so branch where agent overrides is possible
    agent_obj = types.SimpleNamespace(browser_session=bs)

    # Start with a different self.browser_session to force update of self.browser_session inside method
    dummy = DummySelf(browser_session=None, agent=agent_obj)

    # Patch time functions in module to be deterministic
    monkeypatch.setattr(cli.time, 'time', lambda: 1234567890)
    # strftime may be called with (fmt, localtime(...)); ensure it returns deterministic time string
    monkeypatch.setattr(cli.time, 'strftime', lambda fmt, t: '12:34:56')

    cli.BrowserUseApp.update_browser_panel(dummy)

    writes = dummy._last_log.writes
    joined = '\n'.join(writes)

    # Expect Connected status line
    assert any('Connected' in w or '[green]Connected' in w for w in writes), f'got: {writes}'
    # Connection type should be CDP when cdp_url is present
    assert any('Type: [yellow]CDP' in w or 'CDP' in w for w in writes), f'got: {writes}'
    # Window line should be present
    assert any('Window:' in w and '1280' in w and '720' in w for w in writes), f'got: {writes}'
    # Last updated (deterministic string) should be present
    assert any('Last updated: [dim]12:34:56' in w for w in writes), f'got: {writes}'
    # Focused URL should be written and trimmed (ends with ellipsis char)
    assert any('\u2026' in w for w in writes), f'got: {writes}'


# Test 4: Browser session with user-provided executable path (no cdp_url) sets connection_type to 'user-provided'
def test_update_browser_panel_user_provided_executable_round_026(monkeypatch):
    profile = FakeBrowserProfile(headless=False, executable_path='/usr/bin/chromium', viewport=None)
    bs = FakeBrowserSession(cdp_client=object(), cdp_url=None, browser_profile=profile)
    dummy = DummySelf(browser_session=bs, agent=None)

    monkeypatch.setattr(cli.time, 'time', lambda: 1)
    monkeypatch.setattr(cli.time, 'strftime', lambda fmt, t: '00:00:00')

    cli.BrowserUseApp.update_browser_panel(dummy)

    writes = dummy._last_log.writes
    # Should indicate user-provided connection type
    assert any('user-provided' in w for w in writes), f'got: {writes}'
