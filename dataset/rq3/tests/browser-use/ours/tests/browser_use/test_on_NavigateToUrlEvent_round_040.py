import asyncio
from types import SimpleNamespace
import pytest

from browser_use.browser.session import BrowserSession
import browser_use.browser.session as session_mod
from browser_use.browser.events import (
    SwitchTabEvent,
    NavigationCompleteEvent,
    NavigationStartedEvent,
    AgentFocusChangedEvent,
)


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.warn_msgs = []
        self.error_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def warning(self, msg):
        self.warn_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)


class DummySessionManager:
    def __init__(self, current_target=None, page_targets=None):
        self._current = current_target
        self._pages = page_targets or []

    def get_target(self, target_id):
        return self._current

    def get_all_page_targets(self):
        return list(self._pages)


class DummyEventBus:
    def __init__(self, owner):
        self.owner = owner
        self.dispatched = []

    async def dispatch(self, event):
        # Record event
        self.dispatched.append(event)
        # If switching tab, simulate that the agent focus is updated synchronously
        if event.__class__.__name__ == 'SwitchTabEvent':
            # event has attribute target_id
            self.owner.agent_focus_target_id = event.target_id


class DummyTarget:
    def __init__(self, url, target_id):
        self.url = url
        self.target_id = target_id


class DummyEvent:
    def __init__(self, url, new_tab=False, timeout_ms=None, wait_until=None, event_timeout=None):
        self.url = url
        self.new_tab = new_tab
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self.event_timeout = event_timeout


@pytest.mark.asyncio
async def test_navigate_without_connection_round_040(monkeypatch):
    """If agent_focus_target_id is falsy, method should log a warning and return early."""
    bs = BrowserSession.construct()

    # Patch the class-level logger property to return our DummyLogger instance
    dummy_logger = DummyLogger()
    monkeypatch.setattr(session_mod.BrowserSession, 'logger', property(lambda self: dummy_logger), raising=False)

    bs.agent_focus_target_id = None

    # Minimal event
    ev = DummyEvent(url='https://example.com', new_tab=False)

    # Call the async handler
    result = await bs.on_NavigateToUrlEvent(ev)

    # It should return None (exit early) and log a warning
    assert result is None
    assert any('Cannot navigate - browser not connected' in m for m in dummy_logger.warn_msgs)


@pytest.mark.asyncio
async def test_reuse_current_about_blank_tab_no_switch_round_040(monkeypatch):
    """When new_tab=True but current tab is a new-tab page, it should reuse current tab and NOT dispatch SwitchTabEvent."""
    # Arrange
    bs = BrowserSession.construct()

    # Patch logger property
    dummy_logger = DummyLogger()
    monkeypatch.setattr(session_mod.BrowserSession, 'logger', property(lambda self: dummy_logger), raising=False)

    current_id = 'target_current_1234'
    bs.agent_focus_target_id = current_id

    current_target = DummyTarget(url='about:blank', target_id=current_id)
    bs.session_manager = DummySessionManager(current_target=current_target, page_targets=[current_target])

    # Patch is_new_tab_page to return True for about:blank
    monkeypatch.setattr(session_mod, 'is_new_tab_page', lambda url: url == 'about:blank')

    # Event bus that records events
    bs.event_bus = DummyEventBus(bs)

    # Stub navigation and closing functions to record calls
    called = {'navigate': 0, 'closed_ext': 0}

    async def fake_navigate_and_wait(url, target_id, timeout, wait_until, nav_timeout):
        called['navigate'] += 1

    async def fake_close_ext():
        called['closed_ext'] += 1

    bs._navigate_and_wait = fake_navigate_and_wait
    bs._close_extension_options_pages = fake_close_ext

    # Event with new_tab True initially
    ev = DummyEvent(url='https://example.com', new_tab=True, timeout_ms=None, wait_until='load', event_timeout=5)

    # Act
    await bs.on_NavigateToUrlEvent(ev)

    # Assert event.new_tab was toggled to False (reused current tab)
    assert ev.new_tab is False

    # Ensure navigation and extension close were called
    assert called['navigate'] == 1
    assert called['closed_ext'] == 1

    # Check dispatched events include NavigationStartedEvent and NavigationCompleteEvent and AgentFocusChangedEvent
    names = [e.__class__.__name__ for e in bs.event_bus.dispatched]
    assert 'NavigationStartedEvent' in names
    assert 'NavigationCompleteEvent' in names
    assert 'AgentFocusChangedEvent' in names

    # Ensure SwitchTabEvent was NOT dispatched in this reuse scenario
    assert 'SwitchTabEvent' not in names


@pytest.mark.asyncio
async def test_new_tab_create_and_navigation_failure_round_040(monkeypatch):
    """When creating a new tab succeeds but navigation fails later, the outer except should dispatch NavigationCompleteEvent with error_message and AgentFocusChangedEvent and re-raise the original exception."""
    # Arrange
    bs = BrowserSession.construct()

    # Patch logger property
    dummy_logger = DummyLogger()
    monkeypatch.setattr(session_mod.BrowserSession, 'logger', property(lambda self: dummy_logger), raising=False)

    bs.agent_focus_target_id = 'old_target_0001'

    # current target is not a new-tab page
    current_target = DummyTarget(url='https://start.example', target_id=bs.agent_focus_target_id)

    # existing page targets do not contain a reusable about:blank (force creation)
    bs.session_manager = DummySessionManager(current_target=current_target, page_targets=[current_target])

    # Patch is_new_tab_page to return False for current url (so we attempt creation)
    monkeypatch.setattr(session_mod, 'is_new_tab_page', lambda url: False)

    # Event bus that records events and updates agent focus on SwitchTabEvent
    bs.event_bus = DummyEventBus(bs)

    # _cdp_create_new_page returns a new id
    async def fake_create_new_page(url):
        return 'new_target_9999'

    # _navigate_and_wait will raise to trigger outer except
    async def failing_navigate(url, target_id, timeout, wait_until, nav_timeout):
        raise Exception('NAVFAIL')

    async def fake_close_ext():
        # shouldn't be reached because navigation fails
        pass

    bs._cdp_create_new_page = fake_create_new_page
    bs._navigate_and_wait = failing_navigate
    bs._close_extension_options_pages = fake_close_ext

    ev = DummyEvent(url='https://fail.example', new_tab=True, timeout_ms=None, wait_until=None, event_timeout=3)

    # Act & Assert: navigation should raise and we should see NavigationCompleteEvent with error_message recorded
    with pytest.raises(Exception) as excinfo:
        await bs.on_NavigateToUrlEvent(ev)

    assert 'NAVFAIL' in str(excinfo.value)

    # Find dispatched event names and instances
    names = [e.__class__.__name__ for e in bs.event_bus.dispatched]
    assert 'SwitchTabEvent' in names, 'SwitchTabEvent should have been dispatched to switch to new tab'
    assert 'NavigationCompleteEvent' in names, 'NavigationCompleteEvent with error message should have been dispatched in except block'
    assert 'AgentFocusChangedEvent' in names, 'AgentFocusChangedEvent should be dispatched after NavigationCompleteEvent in except block'

    # Verify the NavigationCompleteEvent contains the expected error message
    nav_complete = next((e for e in bs.event_bus.dispatched if e.__class__.__name__ == 'NavigationCompleteEvent'), None)
    assert nav_complete is not None
    assert getattr(nav_complete, 'error_message', None) == 'Exception: NAVFAIL'

    # Ensure the agent focus was updated to the new target when SwitchTabEvent dispatched
    assert bs.agent_focus_target_id == 'new_target_9999'
