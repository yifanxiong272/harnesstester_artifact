# file: browser_use/mcp/server.py:486-569
# asked: {"lines": [502, 503, 505, 506, 508, 509, 512, 514, 515, 517, 518, 520, 521, 522, 523, 524, 525, 528, 529, 531, 532, 533, 534, 535, 536, 538, 539, 541, 542, 543, 544, 545, 546, 548, 549, 551, 552, 554, 555, 557, 558, 560, 561, 563, 564, 566, 567, 569], "branches": [[492, 502], [502, 503], [502, 505], [505, 506], [505, 508], [508, 509], [508, 512], [512, 514], [512, 569], [514, 515], [514, 517], [517, 518], [517, 520], [520, 521], [520, 528], [528, 529], [528, 531], [531, 532], [531, 538], [534, 535], [534, 536], [538, 539], [538, 541], [541, 542], [541, 548], [544, 545], [544, 546], [548, 549], [548, 551], [551, 552], [551, 554], [554, 555], [554, 557], [557, 558], [557, 560], [560, 561], [560, 563], [563, 564], [563, 566], [566, 567], [566, 569]]}
# gained: {"lines": [502, 503, 505, 506, 508, 509, 512, 514, 515, 517, 518, 520, 521, 522, 523, 524, 525, 528, 529, 531, 532, 533, 534, 535, 536, 538, 539, 541, 542, 543, 544, 545, 546, 548, 549, 551, 552, 554, 555, 557, 558, 560, 561, 563, 564, 566, 567, 569], "branches": [[492, 502], [502, 503], [502, 505], [505, 506], [505, 508], [508, 509], [508, 512], [512, 514], [512, 569], [514, 515], [514, 517], [517, 518], [517, 520], [520, 521], [520, 528], [528, 529], [528, 531], [531, 532], [531, 538], [534, 535], [538, 539], [538, 541], [541, 542], [541, 548], [544, 545], [548, 549], [548, 551], [551, 552], [551, 554], [554, 555], [554, 557], [557, 558], [557, 560], [560, 561], [560, 563], [563, 564], [563, 566], [566, 567]]}

import asyncio
import types as pytypes
import pytest

from browser_use.mcp.server import BrowserUseServer
import mcp.types as mcp_types


@pytest.mark.asyncio
async def test_session_management_tools_and_unknown_tool():
    # Create instance without running __init__
    server = object.__new__(BrowserUseServer)

    # Setup minimal attributes used by _execute_tool for session-management branch
    server.browser_session = None
    server.active_sessions = {}
    # Provide async stubs for session management methods
    async def fake_list_sessions():
        return "listed-sessions"
    async def fake_close_session(session_id):
        return f"closed-session:{session_id}"
    async def fake_close_all_sessions():
        return "closed-all"

    server._list_sessions = fake_list_sessions
    server._close_session = fake_close_session
    server._close_all_sessions = fake_close_all_sessions

    # Call browser_list_sessions
    res = await server._execute_tool("browser_list_sessions", {})
    assert res == "listed-sessions"

    # Call browser_close_session
    res = await server._execute_tool("browser_close_session", {"session_id": "sid123"})
    assert res == "closed-session:sid123"

    # Call browser_close_all
    res = await server._execute_tool("browser_close_all", {})
    assert res == "closed-all"

    # Unknown tool should return Unknown tool message
    res = await server._execute_tool("nonexistent_tool", {})
    assert res == "Unknown tool: nonexistent_tool"


@pytest.mark.asyncio
async def test_browser_control_tools_init_and_branches():
    server = object.__new__(BrowserUseServer)

    # Track init calls
    init_calls = {"count": 0}
    async def fake_init_browser_session(allowed_domains=None, **kwargs):
        init_calls["count"] += 1
        # Simulate a browser session object
        server.browser_session = {"id": "session-1"}
        return "inited"

    # Stubs for all browser operations
    async def fake_navigate(url, new_tab=False):
        return f"navigated:{url}:{new_tab}"

    async def fake_click(index=None, coordinate_x=None, coordinate_y=None, new_tab=False):
        return f"clicked:{index}:{coordinate_x}:{coordinate_y}:{new_tab}"

    async def fake_type_text(index, text):
        return f"typed:{index}:{text}"

    async def fake_get_browser_state(include_screenshot=False):
        # return state json and screenshot b64 or None depending on include_screenshot
        if include_screenshot:
            return '{"state":"ok"}', "screenshot-b64"
        return '{"state":"ok"}', None

    async def fake_get_html(selector=None):
        return f"<html sel={selector}>"

    async def fake_screenshot(full_page=False):
        if full_page:
            return '{"meta":"full"}', "screenshot-full-b64"
        return '{"meta":"partial"}', None

    async def fake_extract_content(query, extract_links=False):
        return f"extracted:{query}:{extract_links}"

    async def fake_scroll(direction='down'):
        return f"scrolled:{direction}"

    async def fake_go_back():
        return "went-back"

    async def fake_close_browser():
        # When browser closed, clear server.browser_session
        server.browser_session = None
        return "browser-closed"

    async def fake_list_tabs():
        return "tabs-list"

    async def fake_switch_tab(tab_id):
        return f"switched:{tab_id}"

    async def fake_close_tab(tab_id):
        return f"tab-closed:{tab_id}"

    # Attach stubs
    server._init_browser_session = fake_init_browser_session
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

    # Ensure no browser session initially so _init_browser_session is invoked
    server.browser_session = None

    # 1) browser_navigate triggers init then navigate
    res = await server._execute_tool("browser_navigate", {"url": "http://example", "new_tab": True})
    assert res == "navigated:http://example:True"
    assert init_calls["count"] == 1

    # 2) browser_click should NOT trigger init again (browser_session already set)
    res = await server._execute_tool("browser_click", {"index": 2, "coordinate_x": 10, "coordinate_y": 20, "new_tab": False})
    assert res == "clicked:2:10:20:False"
    assert init_calls["count"] == 1  # no additional init

    # 3) browser_type
    res = await server._execute_tool("browser_type", {"index": 1, "text": "hello"})
    assert res == "typed:1:hello"

    # 4) browser_get_state with screenshot -> returns TextContent and ImageContent
    res = await server._execute_tool("browser_get_state", {"include_screenshot": True})
    assert isinstance(res, list)
    assert len(res) == 2
    txt, img = res
    assert isinstance(txt, mcp_types.TextContent)
    assert txt.type == "text"
    assert txt.text == '{"state":"ok"}'
    assert isinstance(img, mcp_types.ImageContent)
    assert img.type == "image"
    assert img.data == "screenshot-b64"
    assert img.mimeType == "image/png"

    # 5) browser_get_html
    res = await server._execute_tool("browser_get_html", {"selector": "div.main"})
    assert res == "<html sel=div.main>"

    # 6) browser_screenshot with full_page True -> returns text and image
    res = await server._execute_tool("browser_screenshot", {"full_page": True})
    assert isinstance(res, list)
    assert len(res) == 2
    meta, img2 = res
    assert isinstance(meta, mcp_types.TextContent)
    assert meta.text == '{"meta":"full"}'
    assert isinstance(img2, mcp_types.ImageContent)
    assert img2.data == "screenshot-full-b64"

    # 7) browser_extract_content
    res = await server._execute_tool("browser_extract_content", {"query": "h1", "extract_links": True})
    assert res == "extracted:h1:True"

    # 8) browser_scroll
    res = await server._execute_tool("browser_scroll", {"direction": "up"})
    assert res == "scrolled:up"

    # 9) browser_go_back
    res = await server._execute_tool("browser_go_back", {})
    assert res == "went-back"

    # 10) browser_list_tabs
    res = await server._execute_tool("browser_list_tabs", {})
    assert res == "tabs-list"

    # 11) browser_switch_tab
    res = await server._execute_tool("browser_switch_tab", {"tab_id": "tab42"})
    assert res == "switched:tab42"

    # 12) browser_close_tab
    res = await server._execute_tool("browser_close_tab", {"tab_id": "tab99"})
    assert res == "tab-closed:tab99"

    # 13) browser_close should clear browser_session and return expected
    res = await server._execute_tool("browser_close", {})
    assert res == "browser-closed"
    assert server.browser_session is None

    # 14) After closing, calling another browser_xxx should re-init
    res = await server._execute_tool("browser_navigate", {"url": "http://reopen", "new_tab": False})
    assert res == "navigated:http://reopen:False"
    assert init_calls["count"] == 2
