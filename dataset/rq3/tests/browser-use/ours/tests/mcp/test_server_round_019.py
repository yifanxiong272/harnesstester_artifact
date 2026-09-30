import asyncio

from browser_use.mcp.server import BrowserUseServer


def _new_server():
    # Create instance without running __init__ to keep setup minimal and deterministic
    return BrowserUseServer.__new__(BrowserUseServer)


def test_agent_and_list_sessions_round_019():
    server = _new_server()

    # Patch agent tool to a simple deterministic coroutine
    async def fake_retry(task, max_steps=100, model=None, allowed_domains=None, use_vision=True):
        return f"agent:{task}:{max_steps}:{bool(model)}:{bool(allowed_domains)}:{use_vision}"

    server._retry_with_browser_use_agent = fake_retry

    result = asyncio.run(server._execute_tool('retry_with_browser_use_agent', {'task': 'do-it', 'max_steps': 3}))
    assert result == "agent:do-it:3:False:False:True"

    # Patch listing sessions
    async def fake_list_sessions():
        return ["session-1", "session-2"]

    server._list_sessions = fake_list_sessions

    result2 = asyncio.run(server._execute_tool('browser_list_sessions', {}))
    assert result2 == ["session-1", "session-2"]

    # Unknown tool falls back to informative string
    unk = asyncio.run(server._execute_tool('not_a_real_tool', {}))
    assert unk == 'Unknown tool: not_a_real_tool'


def test_browser_direct_tools_init_session_round_019():
    server = _new_server()
    # Start with no browser session to trigger the _init_browser_session branch
    server.browser_session = None

    # init should set browser_session so subsequent calls don't re-init
    called = {"init": 0}

    async def fake_init():
        called["init"] += 1
        server.browser_session = object()
        return None

    server._init_browser_session = fake_init

    # Provide deterministic implementations for the various browser_* helpers.
    async def fake_navigate(url, new_tab=False):
        return f"navigated:{url}:{new_tab}"

    async def fake_click(**kwargs):
        # Accept index, coordinate_x, coordinate_y, new_tab
        return f"clicked:{kwargs.get('index')}:{kwargs.get('new_tab', False)}"

    async def fake_type_text(index, text):
        return f"typed:{index}:{text}"

    async def fake_get_browser_state(include_screenshot=False):
        # Return state_json and a screenshot base64 when include_screenshot True
        if include_screenshot:
            return ("{\"state\":\"ok\"}", "iVBORw0KGgo=")
        return ("{\"state\":\"ok\"}", None)

    async def fake_get_html(selector=None):
        return f"<html selector={selector}/>"

    async def fake_screenshot(full_page=False):
        # Return meta and no screenshot (covers branch where screenshot_b64 is falsy)
        return ("{\"meta\":\"m\"}", None)

    async def fake_extract_content(query, extract_links=False):
        return [f"content for {query}", {"links": extract_links}]

    async def fake_scroll(direction='down'):
        return f"scrolled:{direction}"

    async def fake_go_back():
        return "went-back"

    async def fake_close_browser():
        return "browser-closed"

    async def fake_list_tabs():
        return ["tab-a", "tab-b"]

    async def fake_switch_tab(tab_id):
        return f"switched-to:{tab_id}"

    async def fake_close_tab(tab_id):
        return f"closed-tab:{tab_id}"

    # Attach the fake helpers to the instance. They are plain callables that
    # match how _execute_tool invokes them (no implicit self argument expected).
    server._navigate = fake_navigate
    server._click = fake_click
    server._type_text = fake_type_text
    server._get_browser_state = fake_get_browser_state
    server._get_html = fake_get_html
    server._screenshot = fake_screenshot
    server._extract_content = fake_extract_content
    server._scroll = fake_scroll
    server._go_back = fake_go_back
    server._close_browser = fake_close_browser
    server._list_tabs = fake_list_tabs
    server._switch_tab = fake_switch_tab
    server._close_tab = fake_close_tab

    # 1) Navigate -> should trigger init then navigate
    nav = asyncio.run(server._execute_tool('browser_navigate', {'url': 'http://example', 'new_tab': True}))
    assert nav == 'navigated:http://example:True'
    assert called['init'] == 1  # init called once

    # 2) Click -> should not re-init (browser_session already set)
    click = asyncio.run(server._execute_tool('browser_click', {'index': 2, 'new_tab': False}))
    assert click == 'clicked:2:False'

    # 3) Type -> check arguments passed through
    typed = asyncio.run(server._execute_tool('browser_type', {'index': 0, 'text': 'hello'}))
    assert typed == 'typed:0:hello'

    # 4) Get state with screenshot True -> expect TextContent and ImageContent in returned list
    state_content = asyncio.run(server._execute_tool('browser_get_state', {'include_screenshot': True}))
    # first element must have attribute .text with the JSON string
    assert isinstance(state_content, list)
    assert getattr(state_content[0], 'text') == '{"state":"ok"}'
    # second element must hold the base64 data when include_screenshot=True
    assert getattr(state_content[1], 'data') == 'iVBORw0KGgo='

    # 5) Get HTML
    html = asyncio.run(server._execute_tool('browser_get_html', {'selector': '#id'}))
    assert html == '<html selector=#id/>'

    # 6) Screenshot with no image -> only a TextContent should be returned
    ss = asyncio.run(server._execute_tool('browser_screenshot', {'full_page': False}))
    assert isinstance(ss, list)
    assert getattr(ss[0], 'text') == '{"meta":"m"}'
    assert len(ss) == 1

    # 7) Extract content
    extracted = asyncio.run(server._execute_tool('browser_extract_content', {'query': 'q', 'extract_links': True}))
    assert extracted[0] == 'content for q'
    assert extracted[1] == {'links': True}

    # 8) Scroll, back, close, list tabs, switch and close tab
    assert asyncio.run(server._execute_tool('browser_scroll', {'direction': 'up'})) == 'scrolled:up'
    assert asyncio.run(server._execute_tool('browser_go_back', {})) == 'went-back'
    assert asyncio.run(server._execute_tool('browser_close', {})) == 'browser-closed'
    assert asyncio.run(server._execute_tool('browser_list_tabs', {})) == ["tab-a", "tab-b"]
    assert asyncio.run(server._execute_tool('browser_switch_tab', {'tab_id': 'tab-a'})) == 'switched-to:tab-a'
    assert asyncio.run(server._execute_tool('browser_close_tab', {'tab_id': 'tab-b'})) == 'closed-tab:tab-b'
