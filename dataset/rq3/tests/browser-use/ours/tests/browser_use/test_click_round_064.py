import sys
import types
import asyncio
from types import SimpleNamespace
import pytest

import browser_use.mcp.server as server_mod

# Provide a fake events module that the _click function will import at runtime.
fake_events = types.SimpleNamespace()

class ClickCoordinateEvent:
    def __init__(self, coordinate_x, coordinate_y):
        self.coordinate_x = coordinate_x
        self.coordinate_y = coordinate_y

class NavigateToUrlEvent:
    def __init__(self, url, new_tab=False):
        self.url = url
        self.new_tab = new_tab

class ClickElementEvent:
    def __init__(self, node):
        self.node = node

fake_events.ClickCoordinateEvent = ClickCoordinateEvent
fake_events.NavigateToUrlEvent = NavigateToUrlEvent
fake_events.ClickElementEvent = ClickElementEvent


class DummyEventBus:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        # Record the event object and return an awaitable that resolves deterministically.
        self.dispatched.append(event)

        async def _noop():
            return None

        return _noop()


class DummyElement:
    def __init__(self, attributes):
        self.attributes = attributes


class DummySession:
    def __init__(self, id_="session-1"):
        self.id = id_
        self.event_bus = DummyEventBus()
        # The following can be replaced per-test
        self._element_for_index = None
        self._state = SimpleNamespace(url="http://example.com/current")

    async def get_dom_element_by_index(self, index):
        # Mimic async retrieval
        await asyncio.sleep(0)
        return self._element_for_index

    async def get_browser_state_summary(self):
        await asyncio.sleep(0)
        return self._state


class DummyServer:
    def __init__(self, browser_session=None):
        self.browser_session = browser_session
        self.updated_sessions = []

    def _update_session_activity(self, session_id):
        self.updated_sessions.append(session_id)


@pytest.fixture(autouse=True)
def inject_fake_events(monkeypatch):
    # Ensure the module used by the function-level imports exists and contains our classes
    module_name = 'browser_use.browser.events'
    monkeypatch.setitem(sys.modules, module_name, fake_events)
    yield


@pytest.mark.asyncio
async def test_no_browser_session_round_064():
    srv = DummyServer(browser_session=None)
    # Bind the class method to our dummy instance and call
    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)()
    assert result == 'Error: No browser session active'


@pytest.mark.asyncio
async def test_coordinate_click_round_064():
    sess = DummySession()
    srv = DummyServer(browser_session=sess)

    # Call with coordinates; event bus should get a ClickCoordinateEvent
    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=None, coordinate_x=10, coordinate_y=20, new_tab=False
    )

    assert result == 'Clicked at coordinates (10, 20)'
    # session activity updated
    assert sess.id in srv.updated_sessions
    # verify the dispatched event is of correct fake type and carries coordinates
    dispatched = sess.event_bus.dispatched
    assert dispatched, "expected an event to be dispatched"
    ev = dispatched[-1]
    assert isinstance(ev, ClickCoordinateEvent)
    assert ev.coordinate_x == 10 and ev.coordinate_y == 20


@pytest.mark.asyncio
async def test_index_none_without_coords_round_064():
    sess = DummySession()
    srv = DummyServer(browser_session=sess)

    # No coords and index is None -> error about providing index or coordinates
    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=None, coordinate_x=None, coordinate_y=None, new_tab=False
    )
    assert result == 'Error: Provide either index or both coordinate_x and coordinate_y'


@pytest.mark.asyncio
async def test_element_not_found_round_064():
    sess = DummySession()
    sess._element_for_index = None
    srv = DummyServer(browser_session=sess)

    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=5, coordinate_x=None, coordinate_y=None, new_tab=False
    )
    assert result == 'Element with index 5 not found'


@pytest.mark.asyncio
async def test_new_tab_with_relative_href_round_064():
    sess = DummySession()
    # element with relative href
    sess._element_for_index = DummyElement({'href': '/relative/path'})
    sess._state = SimpleNamespace(url='https://host.example/base')
    srv = DummyServer(browser_session=sess)

    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=2, coordinate_x=None, coordinate_y=None, new_tab=True
    )
    assert result.startswith('Clicked element 2 and opened in new tab ')
    # last dispatched event should be NavigateToUrlEvent with absolute URL
    dispatched = sess.event_bus.dispatched
    assert dispatched, "expected a navigation event"
    nav = dispatched[-1]
    assert isinstance(nav, NavigateToUrlEvent)
    assert nav.new_tab is True
    assert nav.url.startswith('https://host.example')


@pytest.mark.asyncio
async def test_new_tab_with_absolute_href_round_064():
    sess = DummySession()
    # element with absolute href
    sess._element_for_index = DummyElement({'href': 'https://example.org/some/page'})
    srv = DummyServer(browser_session=sess)

    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=3, coordinate_x=None, coordinate_y=None, new_tab=True
    )
    assert 'Clicked element 3 and opened in new tab https' in result
    dispatched = sess.event_bus.dispatched
    assert isinstance(dispatched[-1], NavigateToUrlEvent)
    assert dispatched[-1].url == 'https://example.org/some/page'


@pytest.mark.asyncio
async def test_new_tab_on_non_link_round_064():
    sess = DummySession()
    # element without href -> treated as non-link and normal click dispatched
    sess._element_for_index = DummyElement({})
    srv = DummyServer(browser_session=sess)

    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=7, coordinate_x=None, coordinate_y=None, new_tab=True
    )
    assert result == 'Clicked element 7 (new tab not supported for non-link elements)'
    # Ensure a ClickElementEvent was dispatched
    assert isinstance(sess.event_bus.dispatched[-1], ClickElementEvent)
    assert sess.event_bus.dispatched[-1].node is sess._element_for_index


@pytest.mark.asyncio
async def test_normal_click_round_064():
    sess = DummySession()
    sess._element_for_index = DummyElement({'id': 'btn-1'})
    srv = DummyServer(browser_session=sess)

    result = await server_mod.BrowserUseServer._click.__get__(srv, DummyServer)(
        index=1, coordinate_x=None, coordinate_y=None, new_tab=False
    )
    assert result == 'Clicked element 1'
    assert isinstance(sess.event_bus.dispatched[-1], ClickElementEvent)
    assert sess.event_bus.dispatched[-1].node is sess._element_for_index
