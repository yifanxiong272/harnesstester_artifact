# file: browser_use/browser/session.py:867-975
# asked: {"lines": [869, 870, 871, 872, 874, 875, 878, 879, 880, 881, 883, 885, 887, 888, 889, 892, 893, 894, 895, 896, 897, 900, 901, 902, 903, 904, 906, 907, 908, 910, 911, 914, 917, 918, 919, 922, 924, 926, 927, 931, 934, 935, 936, 937, 938, 939, 943, 946, 947, 948, 949, 950, 951, 954, 963, 964, 966, 967, 968, 969, 970, 971, 974, 975], "branches": [[870, 871], [870, 874], [879, 880], [879, 883], [887, 888], [887, 914], [892, 893], [892, 900], [894, 892], [894, 895], [900, 901], [900, 917], [917, 918], [917, 924], [966, 967], [966, 975]]}
# gained: {"lines": [869, 870, 871, 872, 874, 875, 878, 879, 880, 881, 883, 885, 887, 888, 889, 892, 893, 894, 895, 896, 897, 900, 914, 917, 918, 919, 922, 924, 926, 931, 934, 935, 936, 937, 938, 939, 943, 946, 947, 948, 949, 950, 951, 954, 963, 964, 966, 967, 968, 969, 970, 971, 974, 975], "branches": [[870, 871], [870, 874], [879, 880], [879, 883], [887, 888], [887, 914], [892, 893], [894, 892], [894, 895], [900, 917], [917, 918], [917, 924], [966, 967]]}

import asyncio
from types import SimpleNamespace

import pytest
import importlib


@pytest.mark.asyncio
async def test_on_navigate_to_url_event_early_return(monkeypatch):
    """
    If agent_focus_target_id is not set, on_NavigateToUrlEvent should log a warning and return early
    without dispatching any events.
    """
    session_mod = importlib.import_module('browser_use.browser.session')
    # Replace CloudBrowserClient with a lightweight stub to avoid side effects during BrowserSession instantiation
    class DummyCloudClient:
        def __init__(self): pass

    monkeypatch.setattr(session_mod, 'CloudBrowserClient', DummyCloudClient)

    from browser_use.browser.session import BrowserSession
    from browser_use.browser.events import NavigateToUrlEvent

    session = BrowserSession()
    # Dummy EventBus subclass so pydantic accepts the assignment (isinstance check passes)
    class DummyEventBus(session_mod.EventBus):
        def __init__(self):
            super().__init__()
            self.events = []

        async def dispatch(self, event):
            self.events.append(event)
            return event

    session.event_bus = DummyEventBus()
    # Ensure no agent focus target is set
    session.agent_focus_target_id = None

    event = NavigateToUrlEvent(url='http://example.local/', new_tab=False)
    # Should return without raising and without dispatching anything
    res = await session.on_NavigateToUrlEvent(event)
    assert res is None
    assert session.event_bus.events == []


@pytest.mark.asyncio
async def test_on_navigate_to_url_event_reuses_current_about_blank(monkeypatch):
    """
    If new_tab=True but current tab is an about:blank new tab page, event.new_tab should be set to False,
    and navigation should proceed in the current tab without creating a new one.
    """
    session_mod = importlib.import_module('browser_use.browser.session')

    class DummyCloudClient:
        def __init__(self): pass

    monkeypatch.setattr(session_mod, 'CloudBrowserClient', DummyCloudClient)

    from browser_use.browser.session import BrowserSession
    from browser_use.browser.events import NavigateToUrlEvent

    session = BrowserSession()

    # Dummy session manager to return a current target with about:blank
    current_target = SimpleNamespace(url='about:blank', target_id='target_current_1234')

    class DummySessionManager:
        def get_target(self, target_id):
            assert target_id == current_target.target_id
            return current_target

        def get_all_page_targets(self):
            return [current_target]

    session.session_manager = DummySessionManager()

    # Dummy EventBus subclass so pydantic accepts the assignment (isinstance check passes)
    class DummyEventBus(session_mod.EventBus):
        def __init__(self):
            super().__init__()
            self.events = []

        async def dispatch(self, event):
            self.events.append(event)
            return event

    session.event_bus = DummyEventBus()

    # Replace navigation helpers with stubs
    nav_calls = []

    async def fake_navigate_and_wait(url, target_id, timeout=None, wait_until=None, nav_timeout=None):
        nav_calls.append((url, target_id, timeout, wait_until, nav_timeout))
        await asyncio.sleep(0)

    async def fake_close_ext_options():
        await asyncio.sleep(0)

    session._navigate_and_wait = fake_navigate_and_wait
    session._close_extension_options_pages = fake_close_ext_options

    # Set agent focus to the current target already so SwitchTab isn't dispatched
    session.agent_focus_target_id = current_target.target_id

    # Build event with new_tab True; expecting it to become False due to about:blank reuse
    event = NavigateToUrlEvent(url='http://example.local/page', new_tab=True, timeout_ms=5000, wait_until='load', event_timeout=None)

    await session.on_NavigateToUrlEvent(event)

    # event.new_tab should be mutated to False since current page is about:blank
    assert event.new_tab is False
    # ensure _navigate_and_wait was called with converted timeout 5.0
    assert nav_calls == [('http://example.local/page', current_target.target_id, 5.0, 'load', None)]

    # Ensure dispatch order contains NavigationStartedEvent then NavigationCompleteEvent then AgentFocusChangedEvent
    types = [type(e).__name__ for e in session.event_bus.events]
    assert 'NavigationStartedEvent' in types
    assert 'NavigationCompleteEvent' in types
    assert 'AgentFocusChangedEvent' in types

    # final AgentFocusChangedEvent should reference the same target and url
    af_events = [e for e in session.event_bus.events if type(e).__name__ == 'AgentFocusChangedEvent']
    assert len(af_events) == 1
    af = af_events[0]
    assert af.target_id == current_target.target_id
    assert af.url == 'http://example.local/page'


@pytest.mark.asyncio
async def test_on_navigate_to_url_event_new_tab_reuse_existing_or_create(monkeypatch):
    """
    If new_tab=True and there is an existing about:blank in other tabs, it should reuse that tab.
    Otherwise, it should create a new tab via _cdp_create_new_page and dispatch TabCreatedEvent.
    Also test that SwitchTabEvent updates agent_focus_target_id via event bus handling.
    """
    session_mod = importlib.import_module('browser_use.browser.session')

    class DummyCloudClient:
        def __init__(self): pass

    monkeypatch.setattr(session_mod, 'CloudBrowserClient', DummyCloudClient)

    from browser_use.browser.session import BrowserSession
    from browser_use.browser.events import NavigateToUrlEvent

    session = BrowserSession()

    # current tab is not about:blank
    current_target = SimpleNamespace(url='http://start.local/', target_id='target_current_0001')
    other_blank = SimpleNamespace(url='about:blank', target_id='target_blank_9999')

    class DummySessionManager:
        def get_target(self, target_id):
            return current_target

        def get_all_page_targets(self):
            return [current_target, other_blank]

    session.session_manager = DummySessionManager()

    # Dummy EventBus subclass that records events and updates agent focus on SwitchTabEvent
    class DummyEventBus(session_mod.EventBus):
        def __init__(self, sess):
            super().__init__()
            self.events = []
            self.sess = sess

        async def dispatch(self, event):
            self.events.append(event)
            if type(event).__name__ == 'SwitchTabEvent':
                self.sess.agent_focus_target_id = event.target_id
            return event

    session.event_bus = DummyEventBus(session)

    # Do not create a new page; the reusable about:blank should be selected
    created = []

    async def fake_create_new_page(url='about:blank'):
        created.append(url)
        return 'target_new_1234'

    async def fake_navigate_and_wait(url, target_id, timeout=None, wait_until=None, nav_timeout=None):
        await asyncio.sleep(0)

    async def fake_close_ext_options():
        await asyncio.sleep(0)

    session._cdp_create_new_page = fake_create_new_page
    session._navigate_and_wait = fake_navigate_and_wait
    session._close_extension_options_pages = fake_close_ext_options

    # initial agent focus is on current target; navigating to new_tab True should switch to other_blank
    session.agent_focus_target_id = current_target.target_id

    event = NavigateToUrlEvent(url='http://reuse.example/', new_tab=True, timeout_ms=None, wait_until='load', event_timeout=None)
    await session.on_NavigateToUrlEvent(event)

    # Ensure we reused other_blank and did not create a new page
    assert created == []

    # The event bus should have received a SwitchTabEvent, NavigationStartedEvent, NavigationCompleteEvent, AgentFocusChangedEvent
    names = [type(e).__name__ for e in session.event_bus.events]
    assert 'SwitchTabEvent' in names
    assert 'NavigationStartedEvent' in names
    assert 'NavigationCompleteEvent' in names
    assert 'AgentFocusChangedEvent' in names

    # Verify agent_focus_target_id was updated to the reused blank page
    assert session.agent_focus_target_id == other_blank.target_id

    # Check AgentFocusChangedEvent at end targets the reused blank page and correct url
    af_events = [e for e in session.event_bus.events if type(e).__name__ == 'AgentFocusChangedEvent']
    assert len(af_events) == 1
    af = af_events[0]
    assert af.target_id == other_blank.target_id
    assert af.url == 'http://reuse.example/'


@pytest.mark.asyncio
async def test_on_navigate_to_url_event_navigation_failure_dispatches_error_and_re_raises(monkeypatch):
    """
    If navigation fails (e.g. _navigate_and_wait raises), the outer exception handler should dispatch
    a NavigationCompleteEvent with an error_message and an AgentFocusChangedEvent, then re-raise the exception.
    """
    session_mod = importlib.import_module('browser_use.browser.session')

    class DummyCloudClient:
        def __init__(self): pass

    monkeypatch.setattr(session_mod, 'CloudBrowserClient', DummyCloudClient)

    from browser_use.browser.session import BrowserSession
    from browser_use.browser.events import NavigateToUrlEvent

    session = BrowserSession()

    current_target = SimpleNamespace(url='http://ok.local/', target_id='target_current_err_42')

    class DummySessionManager:
        def get_target(self, target_id):
            return current_target

        def get_all_page_targets(self):
            return [current_target]

    session.session_manager = DummySessionManager()

    # Dummy EventBus subclass to capture dispatched events; on SwitchTabEvent set focus
    class DummyEventBus(session_mod.EventBus):
        def __init__(self, sess):
            super().__init__()
            self.events = []
            self.sess = sess

        async def dispatch(self, event):
            self.events.append(event)
            if type(event).__name__ == 'SwitchTabEvent':
                self.sess.agent_focus_target_id = event.target_id
            return event

    session.event_bus = DummyEventBus(session)

    # _navigate_and_wait will raise to trigger the outer except block
    async def raising_navigate_and_wait(url, target_id, timeout=None, wait_until=None, nav_timeout=None):
        raise RuntimeError('navfail')

    async def fake_close_ext_options():
        await asyncio.sleep(0)

    session._navigate_and_wait = raising_navigate_and_wait
    session._close_extension_options_pages = fake_close_ext_options

    # Set focus to the current target so no switch needed
    session.agent_focus_target_id = current_target.target_id

    event = NavigateToUrlEvent(url='http://will.fail/', new_tab=False, timeout_ms=None, wait_until='load', event_timeout=None)

    with pytest.raises(RuntimeError):
        await session.on_NavigateToUrlEvent(event)

    # After exception, the event bus should have received a NavigationCompleteEvent with an error_message
    complete_events = [e for e in session.event_bus.events if type(e).__name__ == 'NavigationCompleteEvent']
    assert len(complete_events) == 1
    ce = complete_events[0]
    # error_message should include the exception information
    assert ce.error_message is not None
    assert 'RuntimeError' in ce.error_message or 'navfail' in ce.error_message

    # AgentFocusChangedEvent should have been dispatched for the same target and url
    af_events = [e for e in session.event_bus.events if type(e).__name__ == 'AgentFocusChangedEvent']
    assert len(af_events) == 1
    af = af_events[0]
    assert af.target_id == current_target.target_id
    assert af.url == 'http://will.fail/'
