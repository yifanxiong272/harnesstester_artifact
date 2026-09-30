# file: browser_use/cli.py:1236-1320
# asked: {"lines": [1236, 1238, 1239, 1242, 1243, 1244, 1246, 1247, 1249, 1250, 1251, 1254, 1255, 1258, 1259, 1262, 1263, 1264, 1265, 1266, 1269, 1270, 1271, 1272, 1273, 1276, 1277, 1278, 1280, 1283, 1284, 1285, 1286, 1287, 1288, 1291, 1292, 1293, 1295, 1296, 1298, 1299, 1302, 1303, 1305, 1306, 1307, 1308, 1309, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1320], "branches": [[1243, 1244], [1243, 1246], [1246, 1247], [1246, 1320], [1249, 1250], [1249, 1254], [1254, 1255], [1254, 1258], [1263, 1264], [1263, 1265], [1265, 1266], [1265, 1269], [1271, 1272], [1271, 1276], [1283, 1284], [1283, 1291], [1298, 1299], [1298, 1302], [1302, 0], [1302, 1303], [1312, 0], [1312, 1313]]}
# gained: {"lines": [1236, 1238, 1239, 1242, 1243, 1244, 1246, 1247, 1249, 1250, 1251, 1254, 1255, 1258, 1259, 1262, 1263, 1264, 1269, 1270, 1271, 1272, 1273, 1276, 1277, 1278, 1280, 1283, 1284, 1285, 1286, 1291, 1292, 1293, 1295, 1296, 1298, 1299, 1302, 1303, 1305, 1306, 1307, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1320], "branches": [[1243, 1244], [1243, 1246], [1246, 1247], [1246, 1320], [1249, 1250], [1249, 1254], [1254, 1255], [1263, 1264], [1271, 1272], [1283, 1284], [1298, 1299], [1302, 1303], [1312, 1313]]}

import time
import pytest

from browser_use.cli import BrowserUseApp


class FakeRichLog:
    def __init__(self):
        self.lines = []
        self.cleared = False

    def clear(self):
        self.cleared = True
        self.lines.clear()

    def write(self, text):
        # store as str for assertions
        self.lines.append(str(text))


class SimpleViewport:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class SimpleBrowserProfile:
    def __init__(self, headless=False, executable_path=None, viewport=None):
        self.headless = headless
        self.executable_path = executable_path
        self.viewport = viewport


class SimpleTarget:
    def __init__(self, url):
        self.url = url


class SimpleSessionManager:
    def __init__(self, target):
        self._target = target

    def get_focused_target(self):
        return self._target


class SimpleBrowserSession:
    def __init__(
        self,
        cdp_client=None,
        cdp_url=None,
        browser_profile=None,
        agent_focus_target_id=False,
        session_manager=None,
    ):
        self.cdp_client = cdp_client
        self.cdp_url = cdp_url
        self.browser_profile = browser_profile
        self.agent_focus_target_id = agent_focus_target_id
        self.session_manager = session_manager


class BrowserSessionWithCdpRaise:
    """A session where accessing cdp_client raises an exception."""

    def __init__(self, cdp_url=None, browser_profile=None):
        self._cdp_url = cdp_url
        self.browser_profile = browser_profile
        self.agent_focus_target_id = False
        self.session_manager = None

    @property
    def cdp_client(self):
        raise RuntimeError("cdp access failed")

    @cdp_client.setter
    def cdp_client(self, value):
        # allow setting but property always raises on access
        pass

    @property
    def cdp_url(self):
        return self._cdp_url


class TestableApp(BrowserUseApp):
    """A BrowserUseApp variant that avoids textual.App.__init__ side-effects."""

    def __init__(self, config: dict):
        # Intentionally do not call super().__init__ to avoid textual internals.
        # Replicate the minimal state BrowserUseApp.__init__ establishes.
        self.config = config
        self.browser_session = None
        self.controller = None
        self.agent = None
        self.llm = None
        self.task_history = config.get("command_history", [])
        self.history_index = len(self.task_history)
        self._telemetry = None
        self._event_bus_handler_id = None
        self._event_bus_handler_func = None
        self._info_panel_timer = None
        self._richlog = FakeRichLog()

    def query_one(self, selector, widget_type=None):
        # Always return our fake rich log for '#browser-info'
        if selector == "#browser-info":
            return self._richlog
        raise KeyError(f"Unknown selector: {selector}")


def test_update_browser_panel_no_session():
    app = TestableApp(config={})
    # Ensure no browser_session
    app.browser_session = None
    # call method
    app.update_browser_panel()
    # assert RichLog cleared and wrote the 'not initialized' message
    log = app._richlog
    assert log.cleared is True
    # last write should indicate browser not initialized
    assert any("Browser not initialized" in line for line in log.lines)


def test_update_browser_panel_waiting_for_browser():
    app = TestableApp(config={})
    # Create a session with cdp_client set to None (waiting state)
    profile = SimpleBrowserProfile(headless=True)
    session = SimpleBrowserSession(cdp_client=None, cdp_url=None, browser_profile=profile)
    app.browser_session = session
    app.update_browser_panel()
    log = app._richlog
    assert log.cleared is True
    # Should have message waiting for browser to launch and nothing else after return
    assert any("waiting for browser to launch" in line for line in log.lines)
    # Should not contain 'Connected' status
    assert not any("Connected" in line for line in log.lines)


def test_update_browser_panel_connected_with_agent_and_target():
    app = TestableApp(config={})
    # Create a session representing a connected browser via CDP
    viewport = SimpleViewport(800, 600)
    profile = SimpleBrowserProfile(headless=False, executable_path=None, viewport=viewport)
    target = SimpleTarget("https://www.example.com/some/long/path")
    session_manager = SimpleSessionManager(target)
    session = SimpleBrowserSession(
        cdp_client=object(), cdp_url="9222", browser_profile=profile, agent_focus_target_id=True, session_manager=session_manager
    )

    # Set agent to have a browser_session different from app.browser_session to exercise update of self.browser_session
    class AgentStub:
        def __init__(self, bs):
            self.browser_session = bs

    agent = AgentStub(session)
    app.browser_session = None  # ensure difference
    app.agent = agent

    app.update_browser_panel()
    log = app._richlog
    # Should have been cleared
    assert log.cleared is True
    joined = "\n".join(log.lines)
    # Check several expected pieces of output
    assert "Chromium" in joined
    assert "Type:" in joined
    assert "PID:" in joined
    assert "CDP Port: 9222" in joined
    assert "Window:" in joined  # width × height
    assert "Last updated:" in joined
    # eye icon and truncated URL should appear (the code truncates and appends ellipsis)
    assert "👁️" in joined
    # app.browser_session should have been updated to agent's session
    assert app.browser_session is session


def test_update_browser_panel_cdp_client_raises_reports_error_message():
    app = TestableApp(config={})
    # browser_profile still required
    profile = SimpleBrowserProfile(headless=False, viewport=None)
    session = BrowserSessionWithCdpRaise(cdp_url="5555", browser_profile=profile)
    # Place session directly on app (no agent)
    app.browser_session = session

    app.update_browser_panel()
    log = app._richlog
    assert log.cleared is True
    joined = "\n".join(log.lines)
    # Because accessing cdp_client raises early in the method, the outer exception handler writes a single error line
    assert "[red]Error updating browser info: cdp access failed[/]" in joined
    # Ensure no unhandled traceback and that the function did not crash
    assert any("Error updating browser info" in line for line in log.lines)
