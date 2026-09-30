import pytest
from types import SimpleNamespace
import browser_use.mcp.server as server_mod


@pytest.mark.asyncio
async def test_session_tools_round_020():
    """Verify session-management tool dispatching: list, close session, close all."""
    fake_self = SimpleNamespace()

    async def fake_list_sessions():
        return ["s1", "s2"]

    fake_self._list_sessions = fake_list_sessions

    result = await server_mod.BrowserUseServer._execute_tool(fake_self, "browser_list_sessions", {})
    assert result == ["s1", "s2"]

    async def fake_close_session(session_id):
        # observable return based on input to ensure dispatch forwarded argument
        return f"closed:{session_id}"

    fake_self._close_session = fake_close_session

    result = await server_mod.BrowserUseServer._execute_tool(
        fake_self, "browser_close_session", {"session_id": "abc"}
    )
    assert result == "closed:abc"

    async def fake_close_all_sessions():
        return "all_closed"

    fake_self._close_all_sessions = fake_close_all_sessions

    result = await server_mod.BrowserUseServer._execute_tool(fake_self, "browser_close_all", {})
    assert result == "all_closed"


@pytest.mark.asyncio
async def test_browser_direct_control_round_020():
    """Verify browser_ prefix dispatching: ensures session init when needed, and correct forwarding to navigate and click.

    This test injects async stubs onto a fake self object and asserts both return values and side-effects/arguments.
    """
    fake_self = SimpleNamespace()

    # Start with no active browser session to force _init_browser_session path
    fake_self.browser_session = None
    init_called = {"count": 0}

    async def fake_init_browser_session():
        init_called["count"] += 1
        # simulate establishing a session
        fake_self.browser_session = True

    fake_self._init_browser_session = fake_init_browser_session

    async def fake_navigate(url, new_tab=False):
        # return a deterministically formatted string to assert
        return f"navigated:{url}:{new_tab}"

    fake_self._navigate = fake_navigate

    # Call navigate; should call _init_browser_session once first
    res = await server_mod.BrowserUseServer._execute_tool(
        fake_self, "browser_navigate", {"url": "http://example", "new_tab": True}
    )
    assert res == "navigated:http://example:True"
    assert init_called["count"] == 1

    # Now test click forwarding; since browser_session is True, _init_browser_session should not be called again
    clicked = {}

    async def fake_click(index=None, coordinate_x=None, coordinate_y=None, new_tab=False):
        clicked.update({
            "index": index,
            "coordinate_x": coordinate_x,
            "coordinate_y": coordinate_y,
            "new_tab": new_tab,
        })
        return "clicked"

    fake_self._click = fake_click

    res2 = await server_mod.BrowserUseServer._execute_tool(
        fake_self,
        "browser_click",
        {"index": 5, "coordinate_x": 10, "coordinate_y": 20},
    )

    assert res2 == "clicked"
    # verify the exact kwargs forwarded to the click stub
    assert clicked == {
        "index": 5,
        "coordinate_x": 10,
        "coordinate_y": 20,
        "new_tab": False,
    }
    # still only one init call from earlier
    assert init_called["count"] == 1
