# file: browser_use/browser/watchdogs/popups_watchdog.py:27-145
# asked: {"lines": [29, 30, 33, 34, 35, 37, 38, 40, 41, 45, 46, 47, 48, 49, 52, 53, 54, 56, 57, 58, 59, 62, 64, 65, 66, 69, 70, 71, 72, 79, 81, 82, 84, 87, 88, 89, 90, 91, 92, 93, 95, 97, 98, 99, 100, 103, 104, 106, 107, 109, 110, 111, 112, 113, 115, 117, 118, 119, 120, 122, 123, 126, 127, 128, 132, 133, 134, 135, 136, 137, 140, 142, 144, 145], "branches": [[33, 34], [33, 37], [52, 53], [52, 62], [69, 70], [69, 79], [87, 88], [87, 103], [103, 0], [103, 104], [132, 133], [132, 140]]}
# gained: {"lines": [29, 30, 33, 34, 35, 37, 38, 40, 41, 45, 46, 47, 48, 49, 52, 53, 54, 56, 57, 58, 59, 62, 64, 65, 66, 69, 70, 71, 72, 79, 81, 82, 84, 87, 88, 89, 90, 91, 92, 93, 95, 97, 98, 99, 100, 103, 104, 106, 107, 109, 110, 111, 112, 113, 115, 117, 118, 126, 127, 128, 132, 133, 134, 135, 140, 142, 144, 145], "branches": [[33, 34], [33, 37], [52, 53], [69, 70], [87, 88], [103, 0], [103, 104], [132, 133]]}

import asyncio
import pytest

from browser_use.browser.watchdogs.popups_watchdog import PopupsWatchdog

# Patch the logger property on the class to allow instance-level fake logger injection.
# This avoids issues with the original property and pydantic BaseModel mechanics.
PopupsWatchdog.logger = property(lambda self: getattr(self, "_fake_logger", None))


class FakeLogger:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []
        self.warning_msgs = []
        self.error_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def info(self, msg):
        self.info_msgs.append(msg)

    def warning(self, msg):
        self.warning_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)


class FakeSendPage:
    def __init__(self, enable_raises=False, handle_behavior=None):
        """
        handle_behavior: callable(params, session_id) -> coroutine or raises
        enable_raises: if True, enable() will raise Exception
        """
        self._enable_raises = enable_raises
        self.handled_calls = []
        self._handle_behavior = handle_behavior

    async def enable(self, session_id=None):
        if self._enable_raises:
            raise Exception("enable failed")

    async def handleJavaScriptDialog(self, params=None, session_id=None):
        self.handled_calls.append((params, session_id))
        if self._handle_behavior is None:
            return {"result": "ok"}
        outcome = self._handle_behavior(params, session_id)
        if asyncio.iscoroutine(outcome):
            return await outcome
        return outcome


class FakeSend:
    def __init__(self, page: FakeSendPage):
        self.Page = page


class FakeRegisterPage:
    def __init__(self):
        self.registered_callback = None

    def javascriptDialogOpening(self, callback):
        self.registered_callback = callback


class FakeRegister:
    def __init__(self):
        self.Page = FakeRegisterPage()


class FakeCdpClient:
    def __init__(self, send_page: FakeSendPage):
        self.send = FakeSend(send_page)
        self.register = FakeRegister()


class FakeCdpSession:
    def __init__(self, session_id: str, send_page: FakeSendPage):
        self.session_id = session_id
        self.cdp_client = FakeCdpClient(send_page)


class FakeBrowserSession:
    def __init__(self):
        self._closed_popup_messages = []
        self._cdp_client_root = None
        self.agent_focus_target_id = None
        self._sessions = {}
        self.get_or_create_calls = []

    async def get_or_create_cdp_session(self, target_id, focus=True):
        self.get_or_create_calls.append((target_id, focus))
        if target_id not in self._sessions:
            raise RuntimeError("no such session")
        return self._sessions[target_id]


class SimpleEvent:
    def __init__(self, target_id):
        self.target_id = target_id


def make_watchdog_with_browser(fake_browser):
    # Construct instance without invoking BaseModel.__init__
    watchdog = object.__new__(PopupsWatchdog)
    # Set required attributes bypassing pydantic __setattr__ using object.__setattr__
    object.__setattr__(watchdog, "browser_session", fake_browser)
    object.__setattr__(watchdog, "event_bus", None)
    object.__setattr__(watchdog, "_dialog_listeners_registered", set())
    # Install a per-instance fake logger that the patched property will return
    object.__setattr__(watchdog, "_fake_logger", FakeLogger())
    return watchdog


@pytest.mark.asyncio
async def test_on_tab_created_already_registered():
    fake_browser = FakeBrowserSession()
    watchdog = make_watchdog_with_browser(fake_browser)
    target_id = "t1"
    watchdog._dialog_listeners_registered.add(target_id)

    await watchdog.on_TabCreatedEvent(SimpleEvent(target_id))

    assert fake_browser.get_or_create_calls == []
    assert target_id in watchdog._dialog_listeners_registered
    assert any("Already registered dialog handlers" in m for m in watchdog.logger.debug_msgs)


@pytest.mark.asyncio
async def test_on_tab_created_handles_dialog_via_approach1_success():
    fake_browser = FakeBrowserSession()

    root_send_page = FakeSendPage(enable_raises=False)
    fake_root_client = type("RootClient", (), {"send": FakeSend(root_send_page), "register": FakeRegister()})
    fake_browser._cdp_client_root = fake_root_client

    session_send_page = FakeSendPage(enable_raises=False)
    session_id = "session-abc123"
    cdp_session = FakeCdpSession(session_id=session_id, send_page=session_send_page)
    fake_browser._sessions["tab-1"] = cdp_session

    watchdog = make_watchdog_with_browser(fake_browser)

    await watchdog.on_TabCreatedEvent(SimpleEvent("tab-1"))

    registered_cb = cdp_session.cdp_client.register.Page.registered_callback
    assert registered_cb is not None

    assert fake_root_client.register.Page.registered_callback is not None

    await registered_cb({"type": "alert", "message": "Hello"}, session_id=cdp_session.session_id)

    assert any("[alert] Hello" == m for m in fake_browser._closed_popup_messages)
    assert root_send_page.handled_calls, "root handleJavaScriptDialog should have been invoked"
    assert root_send_page.handled_calls[-1][1] == cdp_session.session_id
    assert "tab-1" in watchdog._dialog_listeners_registered
    assert any(
        "Enabled Page domain" in s or "Starting dialog handler setup" in s or "Successfully registered" in s
        for s in watchdog.logger.debug_msgs + watchdog.logger.info_msgs
    )


@pytest.mark.asyncio
async def test_on_tab_created_enable_fail_and_approach2_fallback_and_prompt_dismiss():
    fake_browser = FakeBrowserSession()

    async def handle_behavior(params, session_id):
        if session_id and session_id.endswith("detect"):
            raise asyncio.TimeoutError("simulated timeout")
        return {"result": "ok-via-approach2"}

    root_send_page = FakeSendPage(enable_raises=True, handle_behavior=handle_behavior)
    fake_root_client = type("RootClient", (), {"send": FakeSend(root_send_page), "register": FakeRegister()})
    fake_browser._cdp_client_root = fake_root_client

    session_send_page = FakeSendPage(enable_raises=True)
    detect_session_id = "session-detect"
    detect_cdp_session = FakeCdpSession(session_id=detect_session_id, send_page=session_send_page)
    fake_browser._sessions["tab-2"] = detect_cdp_session

    focus_send_page = FakeSendPage(enable_raises=False)
    focus_session_id = "session-focus"
    focus_cdp_session = FakeCdpSession(session_id=focus_session_id, send_page=focus_send_page)
    fake_browser._sessions["focus-1"] = focus_cdp_session

    fake_browser.agent_focus_target_id = "focus-1"

    watchdog = make_watchdog_with_browser(fake_browser)

    await watchdog.on_TabCreatedEvent(SimpleEvent("tab-2"))

    assert detect_cdp_session.cdp_client.register.Page.registered_callback is not None
    assert fake_root_client.register.Page.registered_callback is not None

    cb = detect_cdp_session.cdp_client.register.Page.registered_callback
    await cb({"type": "prompt", "message": "Enter value"}, session_id=detect_cdp_session.session_id)

    assert any(m == "[prompt] Enter value" for m in fake_browser._closed_popup_messages)
    assert len(root_send_page.handled_calls) >= 2
    assert root_send_page.handled_calls[-1][1] == focus_cdp_session.session_id
    assert "tab-2" in watchdog._dialog_listeners_registered


@pytest.mark.asyncio
async def test_on_tab_created_outer_exception_when_get_session_fails_logs_warning():
    fake_browser = FakeBrowserSession()

    watchdog = make_watchdog_with_browser(fake_browser)

    await watchdog.on_TabCreatedEvent(SimpleEvent("missing-tab"))

    assert "missing-tab" not in watchdog._dialog_listeners_registered
    assert any("Failed to set up popup handling" in m for m in watchdog.logger.warning_msgs)
