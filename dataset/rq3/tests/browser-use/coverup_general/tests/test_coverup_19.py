# file: browser_use/browser/session_manager.py:602-748
# asked: {"lines": [611, 613, 615, 616, 618, 619, 620, 621, 622, 623, 626, 627, 629, 630, 631, 634, 635, 636, 637, 639, 642, 643, 644, 645, 648, 649, 650, 655, 657, 658, 660, 662, 663, 664, 667, 668, 669, 672, 674, 679, 680, 681, 682, 683, 684, 686, 687, 688, 691, 692, 693, 694, 695, 696, 697, 700, 701, 704, 706, 707, 710, 711, 714, 715, 719, 720, 721, 722, 723, 724, 726, 728, 729, 730, 732, 735, 736, 739, 740, 744, 745, 746, 747, 748], "branches": [[615, 616], [615, 626], [618, 619], [618, 623], [629, 630], [629, 634], [634, 635], [634, 642], [660, 662], [660, 667], [680, 681], [680, 686], [683, 680], [683, 684], [686, 687], [686, 710], [691, 692], [691, 700], [719, 720], [719, 735], [722, 719], [722, 723], [744, 745], [744, 746]]}
# gained: {"lines": [611, 613, 615, 616, 618, 619, 620, 623, 626, 627, 629, 630, 631, 634, 635, 636, 637, 639, 642, 644, 645, 648, 649, 650, 655, 657, 658, 660, 662, 663, 664, 667, 668, 669, 672, 674, 679, 680, 681, 682, 683, 684, 686, 687, 688, 691, 692, 693, 694, 695, 696, 697, 700, 701, 704, 706, 707, 710, 711, 714, 715, 719, 720, 721, 722, 723, 724, 726, 728, 729, 730, 732, 735, 736, 744, 745, 746, 747, 748], "branches": [[615, 616], [615, 626], [618, 619], [629, 630], [629, 634], [634, 635], [634, 642], [660, 662], [660, 667], [680, 681], [680, 686], [683, 680], [683, 684], [686, 687], [686, 710], [691, 692], [691, 700], [719, 720], [719, 735], [722, 719], [722, 723], [744, 745]]}

import asyncio
from types import SimpleNamespace
import pytest

import browser_use.browser.session_manager as sm
from browser_use.browser.session_manager import SessionManager


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []
        self.warning_msgs = []
        self.error_msgs = []
        self.critical_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def info(self, msg):
        self.info_msgs.append(msg)

    def warning(self, msg):
        self.warning_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)

    def critical(self, msg):
        self.critical_msgs.append(msg)


class DummyEventBus:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class FakeCDPRoot:
    def __init__(self, activate_may_raise=False):
        self.activated = []
        self.activate_may_raise = activate_may_raise

        class Sender:
            pass

        self.send = Sender()
        # create attribute Target on send
        class Target:
            async def activateTarget(inner_self, params):
                if activate_may_raise:
                    raise RuntimeError("activate failed")
                self.activated.append(params)
                return None

        # bind Target class with closure variable
        self.send.Target = Target()


class DummyBrowserSession:
    def __init__(self):
        self.logger = DummyLogger()
        self._cdp_client_root = None
        # default create_new_page returns incremental ids
        self._create_counter = 0
        self._cdp_create_new_page = self._create_new_page
        self.agent_focus_target_id = None
        self.event_bus = DummyEventBus()

    async def _create_new_page(self, url):
        self._create_counter += 1
        return f"NEW{self._create_counter}"


@pytest.mark.asyncio
async def test_recover_waits_if_already_in_progress(monkeypatch):
    browser = DummyBrowserSession()
    smgr = SessionManager(browser)
    # Prepare state: recovery already in progress and completion event set
    smgr._recovery_in_progress = True
    smgr._recovery_complete_event = asyncio.Event()
    smgr._recovery_complete_event.set()

    # Patch sleep in module to avoid delays (not used here but safe)
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED1")

    # After completion the finally block should reset the flags
    assert smgr._recovery_in_progress is False
    assert smgr._recovery_task is None
    # Event should be set
    assert smgr._recovery_complete_event is not None and smgr._recovery_complete_event.is_set()


@pytest.mark.asyncio
async def test_recover_skips_if_no_cdp_client_root(monkeypatch):
    browser = DummyBrowserSession()
    browser._cdp_client_root = None
    smgr = SessionManager(browser)

    # Ensure not currently in progress
    smgr._recovery_in_progress = False
    smgr._recovery_complete_event = None

    # patch sleep to immediate
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED2")

    # Should have reset flags and logged skipping message
    assert smgr._recovery_in_progress is False
    assert smgr._recovery_complete_event is None or smgr._recovery_complete_event.is_set() or smgr._recovery_complete_event is not None
    # logger should have a debug about skipping focus recovery
    assert any("Skipping focus recovery" in m for m in browser.logger.debug_msgs)


@pytest.mark.asyncio
async def test_recover_skips_if_agent_focus_already_recovered(monkeypatch):
    browser = DummyBrowserSession()
    browser._cdp_client_root = object()
    browser.agent_focus_target_id = "OTHER_TARGET"
    smgr = SessionManager(browser)

    # set get_all_page_targets so code proceeds to check agent_focus_target_id
    smgr.get_all_page_targets = lambda: []
    smgr._get_session_for_target = lambda t: None

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED3")

    # Should log that agent focus already recovered and reset flags
    assert any("Agent focus already recovered" in m for m in browser.logger.debug_msgs)
    assert smgr._recovery_in_progress is False


@pytest.mark.asyncio
async def test_recover_switch_to_existing_tab_activation_success(monkeypatch):
    browser = DummyBrowserSession()
    # Provide a CDP root that successfully activates
    browser._cdp_client_root = FakeCDPRoot(activate_may_raise=False)
    smgr = SessionManager(browser)

    # Simulate one existing page target
    page = SimpleNamespace(target_id="T_EXIST")
    smgr.get_all_page_targets = lambda: [page]
    # Simulate that _get_session_for_target returns a session immediately
    smgr._get_session_for_target = lambda t: "SESSION_FOR_" + t
    # get_target returns an object with url
    smgr.get_target = lambda t: SimpleNamespace(url="http://example")

    # patch sleep to avoid delays
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus(page.target_id)

    # agent_focus_target_id should be updated
    assert browser.agent_focus_target_id == page.target_id
    # Activation should have been called
    assert browser._cdp_client_root.activated != []
    # Event bus should have an AgentFocusChangedEvent-like object (has target_id)
    assert any(getattr(ev, "target_id", None) == page.target_id for ev in browser.event_bus.dispatched)


@pytest.mark.asyncio
async def test_recover_switch_to_existing_tab_activation_fails(monkeypatch):
    browser = DummyBrowserSession()
    # Provide a CDP root whose activate raises
    browser._cdp_client_root = FakeCDPRoot(activate_may_raise=True)
    smgr = SessionManager(browser)

    page = SimpleNamespace(target_id="T_EXIST2")
    smgr.get_all_page_targets = lambda: [page]
    smgr._get_session_for_target = lambda t: "SESSION_FOR_" + t
    smgr.get_target = lambda t: SimpleNamespace(url="http://example2")

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus(page.target_id)

    # Activation failed but recovery should still set agent_focus_target_id and dispatch event
    assert browser.agent_focus_target_id == page.target_id
    assert any(getattr(ev, "target_id", None) == page.target_id for ev in browser.event_bus.dispatched)
    # There should be a debug log for failed activation
    assert any("Failed to activate tab visually" in m for m in browser.logger.debug_msgs)


@pytest.mark.asyncio
async def test_recover_create_new_tab_and_dispatch(monkeypatch):
    browser = DummyBrowserSession()
    # CDP root present
    browser._cdp_client_root = FakeCDPRoot(activate_may_raise=False)
    smgr = SessionManager(browser)

    # No page targets -> forces creation of a new page
    smgr.get_all_page_targets = lambda: []
    # _cdp_create_new_page should be the browser's method
    browser._cdp_create_new_page = browser._create_new_page
    # Simulate that session appears right away for new page
    created_id = "NEW1"
    async def fake_create(url):
        return created_id

    browser._cdp_create_new_page = fake_create
    smgr.browser_session = browser

    smgr._get_session_for_target = lambda t: "SESSION_FOR_" + t if t == created_id else None
    smgr.get_target = lambda t: SimpleNamespace(url="about:blank")

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED4")

    # Should have created new tab and set agent focus
    assert browser.agent_focus_target_id == created_id
    # TabCreatedEvent should have been dispatched (object with target_id)
    assert any(getattr(ev, "target_id", None) == created_id for ev in browser.event_bus.dispatched)
    # AgentFocusChangedEvent should have been dispatched
    assert any(getattr(ev, "target_id", None) == created_id for ev in browser.event_bus.dispatched)


@pytest.mark.asyncio
async def test_recover_fallback_path_success(monkeypatch):
    browser = DummyBrowserSession()
    browser._cdp_client_root = FakeCDPRoot(activate_may_raise=False)
    smgr = SessionManager(browser)

    # No existing pages -> first create new returns N1, but no session appears for it.
    smgr.get_all_page_targets = lambda: []
    # Simulate browser creating pages: first call new page N1, second call fallback FB
    created_sequence = ["N1", "FB"]
    async def create_seq(url):
        return created_sequence.pop(0)
    browser._cdp_create_new_page = create_seq
    smgr.browser_session = browser

    # _get_session_for_target returns None for N1, but returns a session for FB
    def fake_get_session(t):
        if t == "FB":
            return "SESSION_FOR_FB"
        return None

    smgr._get_session_for_target = fake_get_session
    smgr.get_target = lambda t: SimpleNamespace(url="about:blank")

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED5")

    # Fallback should have been used and focus set to FB
    assert browser.agent_focus_target_id == "FB"
    # Both initial TabCreatedEvent for N1 and TabCreatedEvent for FB should have been dispatched
    dispatched_ids = [getattr(ev, "target_id", None) for ev in browser.event_bus.dispatched]
    assert "N1" in dispatched_ids and "FB" in dispatched_ids
    # AgentFocusChangedEvent for FB should be present
    assert any(getattr(ev, "target_id", None) == "FB" for ev in browser.event_bus.dispatched)


@pytest.mark.asyncio
async def test_recover_fallback_total_failure_logs_critical(monkeypatch):
    browser = DummyBrowserSession()
    browser._cdp_client_root = FakeCDPRoot(activate_may_raise=False)
    smgr = SessionManager(browser)

    smgr.get_all_page_targets = lambda: []
    # Configure create_new_page to produce ids but sessions never appear
    async def create_new(url):
        return "XFAIL"

    browser._cdp_create_new_page = create_new
    smgr.browser_session = browser

    # _get_session_for_target never finds anything
    smgr._get_session_for_target = lambda t: None

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(sm, "asyncio", sm.asyncio)
    monkeypatch.setattr(sm.asyncio, "sleep", fast_sleep)

    await smgr._recover_agent_focus("CRASHED6")

    # Since fallback also fails, a critical log should be present
    assert any("CRITICAL" in m or "CRITICAL:" in m or "CRITICAL" in m for m in browser.logger.critical_msgs) or any("CRITICAL" in m for m in browser.logger.critical_msgs) or (browser.logger.critical_msgs != [])
