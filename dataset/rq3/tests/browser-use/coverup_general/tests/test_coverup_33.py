# file: browser_use/browser/session_manager.py:497-600
# asked: {"lines": [503, 504, 507, 508, 509, 511, 512, 513, 515, 516, 517, 519, 521, 522, 524, 526, 527, 528, 532, 533, 535, 538, 541, 542, 543, 546, 549, 550, 553, 554, 555, 556, 560, 563, 564, 565, 569, 570, 571, 572, 576, 577, 580, 581, 582, 584, 585, 586, 587, 588, 592, 594, 595, 596, 597, 598, 599], "branches": [[507, 508], [507, 511], [511, 512], [511, 515], [521, 522], [521, 563], [532, 533], [532, 569], [541, 542], [541, 549], [553, 554], [553, 560], [569, 570], [569, 576], [576, 577], [576, 580], [580, 581], [580, 592], [581, 582], [581, 586], [586, 587], [586, 592], [592, 0], [592, 594], [594, 0], [594, 595]]}
# gained: {"lines": [503, 504, 507, 508, 509, 511, 512, 513, 515, 516, 517, 519, 521, 522, 524, 526, 527, 528, 532, 533, 535, 538, 541, 542, 543, 546, 549, 550, 553, 554, 555, 556, 560, 569, 570, 571, 572, 576, 577, 580, 581, 582, 584, 585, 586, 587, 588, 592, 594, 595, 596, 597, 598, 599], "branches": [[507, 508], [507, 511], [511, 512], [511, 515], [521, 522], [532, 533], [532, 569], [541, 542], [541, 549], [553, 554], [569, 570], [576, 577], [580, 581], [580, 592], [581, 582], [581, 586], [586, 587], [592, 0], [592, 594], [594, 595]]}

import asyncio
import pytest

from browser_use.browser import session_manager as sm_mod
from browser_use.browser.session_manager import SessionManager


class DummyLogger:
    def __init__(self):
        self.debug_messages = []
        self.warning_messages = []

    def debug(self, msg):
        self.debug_messages.append(msg)

    def warning(self, msg):
        self.warning_messages.append(msg)


class DummyEventBus:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class DummyBrowserSession:
    def __init__(self):
        self.logger = DummyLogger()
        self.event_bus = DummyEventBus()
        # This is the attribute used by SessionManager
        self.agent_focus_target_id = None


class DummyTarget:
    def __init__(self, target_type):
        self.target_type = target_type


class DummySession:
    def __init__(self, sid):
        self.id = sid


@pytest.mark.asyncio
async def test_handle_target_detached_unknown_target_logs_warning(monkeypatch):
    browser = DummyBrowserSession()
    manager = SessionManager(browser)

    # Ensure clean mappings
    manager._targets = {}
    manager._sessions = {}
    manager._target_sessions = {}
    manager._session_to_target = {}

    # Replace create_task_with_error_handling to detect unexpected calls
    called = {"create_task": False}

    def fake_create_task(coro, name=None, logger_instance=None, suppress_exceptions=None):
        called["create_task"] = True
        return object()

    monkeypatch.setattr(sm_mod, "create_task_with_error_handling", fake_create_task)

    # Event with sessionId but no targetId and no mapping -> should log warning and return
    event = {"sessionId": "session_unknown"}
    await manager._handle_target_detached(event)

    # Assert warning logged and no create_task called and nothing removed
    assert any("Session detached but target unknown" in m for m in browser.logger.warning_messages)
    assert called["create_task"] is False
    assert manager._targets == {}
    assert manager._sessions == {}
    assert manager._target_sessions == {}
    assert manager._session_to_target == {}


@pytest.mark.asyncio
async def test_handle_target_detached_remaining_sessions_keeps_target(monkeypatch):
    browser = DummyBrowserSession()
    manager = SessionManager(browser)

    # Setup a target with two sessions; remove one should leave the target intact
    target_id = "target_1"
    session_id = "s1"
    other_session = "s2"
    manager._targets = {target_id: DummyTarget("page")}
    manager._sessions = {session_id: DummySession(session_id), other_session: DummySession(other_session)}
    manager._target_sessions = {target_id: {session_id, other_session}}
    manager._session_to_target = {session_id: target_id, other_session: target_id}

    called = {"create_task": False}

    def fake_create_task(coro, name=None, logger_instance=None, suppress_exceptions=None):
        called["create_task"] = True
        return object()

    monkeypatch.setattr(sm_mod, "create_task_with_error_handling", fake_create_task)

    # Event includes targetId (so lookup branch not taken), detach s1
    event = {"sessionId": session_id, "targetId": target_id}
    await manager._handle_target_detached(event)

    # s1 removed from sessions and mapping, target remains, other session still present
    assert session_id not in manager._sessions
    assert session_id not in manager._session_to_target
    assert other_session in manager._sessions
    assert target_id in manager._targets
    assert manager._target_sessions[target_id] == {other_session}
    # No recovery task should have been created (agent focus not lost)
    assert called["create_task"] is False
    # No TabClosedEvent should have been dispatched
    assert browser.event_bus.dispatched == []


@pytest.mark.asyncio
async def test_handle_target_detached_last_session_page_target_triggers_tab_closed_and_recovery(monkeypatch):
    browser = DummyBrowserSession()
    manager = SessionManager(browser)

    target_id = "target_page"
    session_id = "s_last"

    # Setup single-session target that will be fully removed
    manager._targets = {target_id: DummyTarget("page")}
    manager._sessions = {session_id: DummySession(session_id)}
    manager._target_sessions = {target_id: {session_id}}
    manager._session_to_target = {session_id: target_id}

    # Set agent focus to this target to force agent_focus_lost path
    browser.agent_focus_target_id = target_id

    # Prepare a fake recover coroutine to check it was passed into create_task_with_error_handling
    async def fake_recover(tid):
        # return tid so we can verify awaiting the coroutine yields expected target_id
        return tid

    # Patch the instance method _recover_agent_focus to our fake
    manager._recover_agent_focus = lambda tid: fake_recover(tid)

    recorded = {}

    def fake_create_task(coro, name=None, logger_instance=None, suppress_exceptions=None):
        # record that it was called and the coroutine object; return a dummy task object
        recorded["called"] = True
        recorded["coro"] = coro
        recorded["name"] = name
        recorded["logger_instance"] = logger_instance
        recorded["suppress_exceptions"] = suppress_exceptions
        return "dummy_task"

    # monkeypatch the module-level create_task_with_error_handling
    monkeypatch.setattr(sm_mod, "create_task_with_error_handling", fake_create_task)

    # Event without targetId to force lookup via _session_to_target
    event = {"sessionId": session_id}
    await manager._handle_target_detached(event)

    # Target and session removed from manager state
    assert target_id not in manager._targets
    assert target_id not in manager._target_sessions
    assert session_id not in manager._sessions
    assert session_id not in manager._session_to_target

    # Agent focus should have been cleared
    assert browser.agent_focus_target_id is None

    # TabClosedEvent should have been dispatched (type 'page')
    dispatched = browser.event_bus.dispatched
    assert len(dispatched) == 1
    # Import here to avoid top-level import requirements
    from browser_use.browser.events import TabClosedEvent
    assert isinstance(dispatched[0], TabClosedEvent)
    assert dispatched[0].target_id == target_id

    # Recovery should have been started via create_task_with_error_handling
    assert recorded.get("called", False) is True
    assert recorded.get("name") == "recover_agent_focus"
    assert recorded.get("logger_instance") is browser.logger
    assert recorded.get("suppress_exceptions") is False

    # The coroutine passed should be awaitable and when awaited return the target id
    coro = recorded["coro"]
    assert asyncio.iscoroutine(coro)
    result = await coro
    assert result == target_id

    # Manager should have stored the returned task
    assert manager._recovery_task == "dummy_task"


@pytest.mark.asyncio
async def test_handle_target_detached_last_session_non_page_does_not_dispatch_tab_closed(monkeypatch):
    browser = DummyBrowserSession()
    manager = SessionManager(browser)

    target_id = "target_worker"
    session_id = "s_worker"

    # Setup single-session target of type 'worker' that will be fully removed
    manager._targets = {target_id: DummyTarget("worker")}
    manager._sessions = {session_id: DummySession(session_id)}
    manager._target_sessions = {target_id: {session_id}}
    manager._session_to_target = {session_id: target_id}

    # Ensure agent focus not pointing to this target
    browser.agent_focus_target_id = "some_other_target"

    called = {"create_task": False}

    def fake_create_task(coro, name=None, logger_instance=None, suppress_exceptions=None):
        called["create_task"] = True
        return object()

    monkeypatch.setattr(sm_mod, "create_task_with_error_handling", fake_create_task)

    # Detach; since target_type is 'worker' we should not dispatch TabClosedEvent
    event = {"sessionId": session_id}
    await manager._handle_target_detached(event)

    # Ensure no TabClosedEvent dispatched and target removed
    assert browser.event_bus.dispatched == []
    assert target_id not in manager._targets
    assert target_id not in manager._target_sessions
    # create_task should not be called because agent_focus_lost is False
    assert called["create_task"] is False
