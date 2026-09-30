# file: browser_use/cli.py:1236-1320
# asked: {"lines": [1236, 1238, 1239, 1242, 1243, 1244, 1246, 1247, 1249, 1250, 1251, 1254, 1255, 1258, 1259, 1262, 1263, 1264, 1265, 1266, 1269, 1270, 1271, 1272, 1273, 1276, 1277, 1278, 1280, 1283, 1284, 1285, 1286, 1287, 1288, 1291, 1292, 1293, 1295, 1296, 1298, 1299, 1302, 1303, 1305, 1306, 1307, 1308, 1309, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1320], "branches": [[1243, 1244], [1243, 1246], [1246, 1247], [1246, 1320], [1249, 1250], [1249, 1254], [1254, 1255], [1254, 1258], [1263, 1264], [1263, 1265], [1265, 1266], [1265, 1269], [1271, 1272], [1271, 1276], [1283, 1284], [1283, 1291], [1298, 1299], [1298, 1302], [1302, 0], [1302, 1303], [1312, 0], [1312, 1313]]}
# gained: {"lines": [1236, 1238, 1239, 1242, 1243, 1244, 1246, 1247, 1249, 1250, 1251, 1254, 1255, 1258, 1259, 1262, 1263, 1264, 1269, 1270, 1271, 1272, 1273, 1276, 1277, 1278, 1280, 1283, 1284, 1285, 1286, 1291, 1292, 1293, 1295, 1296, 1298, 1299, 1302, 1303, 1305, 1306, 1307, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1320], "branches": [[1243, 1244], [1243, 1246], [1246, 1247], [1246, 1320], [1249, 1250], [1249, 1254], [1254, 1255], [1263, 1264], [1271, 1272], [1283, 1284], [1298, 1299], [1302, 1303], [1312, 1313]]}

import time
from types import SimpleNamespace

import pytest

from browser_use.cli import BrowserUseApp


class FakeRichLog:
    def __init__(self):
        self.writes = []
        self.cleared = False

    def clear(self):
        self.cleared = True

    def write(self, msg):
        self.writes.append(msg)


def make_browser_profile(headless=False, width=None, height=None, executable_path=""):
    viewport = None
    if width is not None and height is not None:
        viewport = SimpleNamespace(width=width, height=height)
    return SimpleNamespace(headless=headless, viewport=viewport, executable_path=executable_path)


def make_session(
    cdp_client=None,
    cdp_url=None,
    profile=None,
    agent_focus_target_id=False,
    focused_url=None,
):
    # profile may be None to trigger attribute errors in tests
    session_manager = SimpleNamespace()
    if focused_url is None:
        session_manager.get_focused_target = lambda: None
    else:
        session_manager.get_focused_target = lambda: SimpleNamespace(url=focused_url)
    return SimpleNamespace(
        cdp_client=cdp_client,
        cdp_url=cdp_url,
        browser_profile=profile,
        session_manager=session_manager,
        agent_focus_target_id=agent_focus_target_id,
    )


def setup_app_with_fake_log(monkeypatch):
    app = BrowserUseApp(config={})
    fake_log = FakeRichLog()
    # Replace query_one on the instance to always return our fake log
    monkeypatch.setattr(app, "query_one", lambda selector, cls=None: fake_log)
    return app, fake_log


def test_update_browser_panel_not_initialized(monkeypatch):
    app, fake_log = setup_app_with_fake_log(monkeypatch)
    app.browser_session = None

    app.update_browser_panel()

    assert fake_log.cleared is True
    assert fake_log.writes == ['[red]Browser not initialized[/]']


def test_update_browser_panel_waiting_for_launch_when_no_cdp_client(monkeypatch):
    app, fake_log = setup_app_with_fake_log(monkeypatch)

    # Browser session exists but cdp_client is None => waiting message + early return
    session = make_session(cdp_client=None, profile=make_browser_profile(headless=False))
    app.browser_session = session

    app.update_browser_panel()

    assert fake_log.cleared is True
    assert fake_log.writes == ['[yellow]Browser session created, waiting for browser to launch...[/]']


def test_update_browser_panel_connected_and_agent_focus_and_window(monkeypatch):
    app, fake_log = setup_app_with_fake_log(monkeypatch)

    # Create a browser session that will be provided by agent (to force the assignment branch)
    session = make_session(
        cdp_client=object(),
        cdp_url="ws://127.0.0.1:9222",
        profile=make_browser_profile(headless=True, width=1280, height=720, executable_path=""),
        agent_focus_target_id=True,
        focused_url="https://www.example.com/page",
    )

    # app.browser_session starts as None, agent provides session -> should assign app.browser_session
    app.browser_session = None
    app.agent = SimpleNamespace(browser_session=session)

    # Fix time to deterministic value
    monkeypatch.setattr(time, "time", lambda: 1600000000)

    app.update_browser_panel()

    # There should be multiple writes; check critical content exists
    written = "\n".join(fake_log.writes)
    assert "Chromium" in written
    assert "Connected" in written  # status
    assert "Type: [yellow]CDP[/]" in written  # connection type due to cdp_url present
    assert "PID: [dim]N/A[/]" in written or "PID: [dim]" in written
    assert "CDP Port: ws://127.0.0.1:9222" in written
    assert "Window: [blue]1280[/] × [blue]720[/]" in written
    # The current url should have www removed and end with ellipsis per implementation
    assert "example.com/page…[/]" in written or "example.com/page…" in written
    # Ensure the agent-provided session was assigned back to app.browser_session
    assert app.browser_session is session


def test_update_browser_panel_outer_exception_writes_error(monkeypatch):
    app, fake_log = setup_app_with_fake_log(monkeypatch)

    # Create a connected session with browser_profile set to None to trigger AttributeError
    session = make_session(
        cdp_client=object(),
        cdp_url="ws://127.0.0.1:9222",
        profile=None,
        agent_focus_target_id=False,
    )
    app.browser_session = None
    app.agent = SimpleNamespace(browser_session=session)

    app.update_browser_panel()

    # Confirm that an error message was written by the outer except block
    assert any("Error updating browser info:" in w for w in fake_log.writes)
    # And that the specific attribute error message is present
    assert any("NoneType" in w and "headless" in w for w in fake_log.writes)
