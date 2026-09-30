import json
import pytest

from browser_use.mcp import server as server_module
from browser_use.mcp.server import BrowserUseServer

# Small deterministic fakes to simulate browser session state and DOM elements
class FakeTab:
    def __init__(self, url: str, title: str):
        self.url = url
        self.title = title


class FakePageInfo:
    def __init__(self, viewport_width=800, viewport_height=600, page_width=1200, page_height=2000, scroll_x=10, scroll_y=20):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.page_width = page_width
        self.page_height = page_height
        self.scroll_x = scroll_x
        self.scroll_y = scroll_y


class FakeElement:
    def __init__(self, tag_name: str, children_text: str, attributes: dict[str, str] | None = None):
        self.tag_name = tag_name
        self._children_text = children_text
        self.attributes = attributes or {}

    def get_all_children_text(self, max_depth: int = 2):
        # deterministic short-circuiting behavior
        return self._children_text


class FakeDomState:
    def __init__(self, selector_map: dict[int, FakeElement]):
        self.selector_map = selector_map


class FakeState:
    def __init__(self, *, url="http://example", title="Example Title", tabs=None, page_info=None, dom_state=None, screenshot=None):
        self.url = url
        self.title = title
        self.tabs = tabs or []
        self.page_info = page_info
        self.dom_state = dom_state
        self.screenshot = screenshot


class FakeBrowserSession:
    def __init__(self, state: FakeState):
        self._state = state

    async def get_browser_state_summary(self):
        # emulate async retrieval
        return self._state


@pytest.mark.asyncio
async def test_no_browser_session_returns_error_round_098():
    # Create a BrowserUseServer instance without running its __init__ to avoid side effects
    server = object.__new__(BrowserUseServer)
    # Ensure no browser_session is active to hit the 'no session' branch
    server.browser_session = None

    state_json, screenshot = await server._get_browser_state(include_screenshot=False)

    assert state_json == 'Error: No browser session active'
    assert screenshot is None


@pytest.mark.asyncio
async def test_full_state_with_pageinfo_and_screenshot_round_098():
    server = object.__new__(BrowserUseServer)

    # Build two DOM elements to exercise placeholder and href branches
    el1 = FakeElement(tag_name='input', children_text='Enter name', attributes={'placeholder': 'Name'})
    el2 = FakeElement(tag_name='a', children_text='Click here', attributes={'href': 'https://x.example'})

    dom_state = FakeDomState(selector_map={1: el1, 2: el2})
    tabs = [FakeTab(url='http://a', title='A'), FakeTab(url='http://b', title='B')]
    page_info = FakePageInfo(viewport_width=1024, viewport_height=768, page_width=2000, page_height=3000, scroll_x=100, scroll_y=200)

    fake_state = FakeState(url='http://site', title='Site Title', tabs=tabs, page_info=page_info, dom_state=dom_state, screenshot='IMG_BASE64')
    server.browser_session = FakeBrowserSession(fake_state)

    json_str, screenshot_b64 = await server._get_browser_state(include_screenshot=True)

    parsed = json.loads(json_str)

    # Basic top-level assertions
    assert parsed['url'] == 'http://site'
    assert parsed['title'] == 'Site Title'
    assert isinstance(parsed['tabs'], list) and len(parsed['tabs']) == 2

    # Page info should have been added to JSON
    assert 'viewport' in parsed and parsed['viewport']['width'] == 1024 and parsed['viewport']['height'] == 768
    assert 'page' in parsed and parsed['page']['width'] == 2000 and parsed['page']['height'] == 3000
    assert 'scroll' in parsed and parsed['scroll']['x'] == 100 and parsed['scroll']['y'] == 200

    # Interactive elements: ensure placeholder and href branches created keys
    ie = parsed['interactive_elements']
    assert any(item.get('placeholder') == 'Name' for item in ie)
    assert any(item.get('href') == 'https://x.example' for item in ie)

    # Screenshot should be returned separately and dimensions included
    assert screenshot_b64 == 'IMG_BASE64'
    assert 'screenshot_dimensions' in parsed
    assert parsed['screenshot_dimensions']['width'] == 1024
    assert parsed['screenshot_dimensions']['height'] == 768


@pytest.mark.asyncio
async def test_state_without_pageinfo_no_screenshot_dimensions_round_098():
    server = object.__new__(BrowserUseServer)

    # When page_info is None, viewport/page/scroll should not be added
    element = FakeElement(tag_name='p', children_text='Paragraph', attributes={})
    dom_state = FakeDomState(selector_map={0: element})
    tabs = [FakeTab(url='http://only', title='Only')]

    fake_state = FakeState(url='http://noinfo', title='No Info', tabs=tabs, page_info=None, dom_state=dom_state, screenshot='IMG_B64')
    server.browser_session = FakeBrowserSession(fake_state)

    json_str, screenshot_b64 = await server._get_browser_state(include_screenshot=True)

    parsed = json.loads(json_str)

    assert 'viewport' not in parsed
    assert 'page' not in parsed
    assert 'scroll' not in parsed

    # Because page_info is None, screenshot_dimensions should NOT be added even though screenshot exists
    assert screenshot_b64 == 'IMG_B64'
    assert 'screenshot_dimensions' not in parsed
