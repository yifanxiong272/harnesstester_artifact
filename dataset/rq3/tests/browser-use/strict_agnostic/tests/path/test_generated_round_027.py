import types
import pytest

import browser_use.cli as cli


class FakeRichLog:
    def __init__(self):
        self.writes = []
        self.cleared = False

    def clear(self):
        self.cleared = True

    def write(self, msg):
        # normalize to str to avoid surprises
        self.writes.append(str(msg))


class FakeViewport:
    def __init__(self, width=None, height=None):
        self.width = width
        self.height = height


class FakeBrowserProfile:
    def __init__(self, headless=False, executable_path=None, viewport=None):
        self.headless = headless
        self.executable_path = executable_path
        self.viewport = viewport


class FakeTarget:
    def __init__(self, url):
        self.url = url


class FakeSessionManager:
    def __init__(self, target=None):
        self._target = target

    def get_focused_target(self):
        return self._target


class FakeBrowserSession:
    def __init__(self, *, cdp_client=None, cdp_url=None, profile=None, agent_focus_target_id=False, session_manager=None):
        self.cdp_client = cdp_client
        self.cdp_url = cdp_url
        self.browser_profile = profile or FakeBrowserProfile()
        self.agent_focus_target_id = agent_focus_target_id
        self.session_manager = session_manager


class DummySelf:
    def __init__(self, browser_session=None, agent=None):
        self._rich = FakeRichLog()
        self.browser_session = browser_session
        # agent can be any object; when present it may have .browser_session
        self.agent = agent

    def query_one(self, selector, widget):
        # ignore widget type; always return our fake log
        return self._rich


def test_no_browser_session_round_027():
    """If self.browser_session is None and no agent present, the UI should report not initialized."""
    dummy = DummySelf(browser_session=None, agent=None)

    # Call the real method under test. The method is defined on the class; call with our dummy instance.
    cli.BrowserUseApp.update_browser_panel(dummy)

    # After calling, the panel should have been cleared and should show 'Browser not initialized'
    assert dummy._rich.cleared is True
    assert any('Browser not initialized' in w for w in dummy._rich.writes), f"writes: {dummy._rich.writes}"


def test_browser_session_no_cdp_client_round_027():
    """If browser_session exists but has no cdp_client, the function should report waiting for launch and return early."""
    profile = FakeBrowserProfile(headless=False)
    session = FakeBrowserSession(cdp_client=None, cdp_url=None, profile=profile)
    dummy = DummySelf(browser_session=session, agent=None)

    cli.BrowserUseApp.update_browser_panel(dummy)

    # Should clear first
    assert dummy._rich.cleared is True
    # Should contain the 'waiting for browser to launch' message and return early (so no connected/PID lines)
    assert any('waiting for browser to launch' in w for w in dummy._rich.writes), dummy._rich.writes
    assert not any('Connected' in w or 'PID:' in w for w in dummy._rich.writes)


def test_connected_browser_with_agent_and_focus_round_027(monkeypatch):
    """Exercise the connected path, CDP connection_type, viewport display, session update, and agent-focused URL.

    This test patches time functions in the module under test to be deterministic.
    """
    # Prepare a deterministic time display
    fixed_time = 1_600_000_000  # epoch

    # Patch the time functions inside the module under test (cli)
    monkeypatch.setattr(cli.time, 'time', lambda: fixed_time)
    monkeypatch.setattr(cli.time, 'localtime', lambda ts: (0, 0, 0, 0, 0, 0, 0, 0, 0))
    # time.strftime is expected to accept format and time tuple; return predictable string
    monkeypatch.setattr(cli.time, 'strftime', lambda fmt, t: '12:34:56')

    # Prepare viewport and profile
    viewport = FakeViewport(width=800, height=600)
    profile = FakeBrowserProfile(headless=True, executable_path='/usr/bin/chrome', viewport=viewport)

    # Prepare a focused target URL
    target = FakeTarget(url='https://www.example.com/some/path')
    session_manager = FakeSessionManager(target=target)

    # cdp_client non-None indicates presence of CDP client (connected path)
    browser_session = FakeBrowserSession(cdp_client=object(), cdp_url='http://127.0.0.1:9222', profile=profile, agent_focus_target_id=True, session_manager=session_manager)

    # Set dummy.self.browser_session to a different object to force update of self.browser_session inside the method
    other_session = FakeBrowserSession()
    # agent object that also holds a browser_session (simulate agent's session)
    class Agent:
        def __init__(self, browser_session):
            self.browser_session = browser_session

    agent = Agent(browser_session)

    dummy = DummySelf(browser_session=other_session, agent=agent)

    # Run the method
    cli.BrowserUseApp.update_browser_panel(dummy)

    # After calling, self.browser_session should have been updated to the agent's browser_session
    assert dummy.browser_session is browser_session

    writes = '\n'.join(dummy._rich.writes)

    # Should indicate Chromium and Connected
    assert 'Chromium' in writes
    assert 'Connected' in writes

    # Should include the connection type (CDP) and headless marker (red) because profile.headless True
    assert 'CDP' in writes
    assert '(headless)' in writes or 'headless' in writes

    # Should show the PID as N/A when cdp_client is present
    assert 'PID' in writes
    assert 'N/A' in writes

    # Should show the CDP port equal to the cdp_url
    assert 'http://127.0.0.1:9222' in writes

    # Should show the window size
    assert '800' in writes and '600' in writes

    # Should include a deterministic last-updated line added by our patched time.strftime
    assert 'Last updated' in writes
    assert '12:34:56' in writes

    # Should include the agent focused URL (shortened and with ellipsis)
    assert '\u2026' in writes or '…' in writes
    assert 'example.com' in writes
