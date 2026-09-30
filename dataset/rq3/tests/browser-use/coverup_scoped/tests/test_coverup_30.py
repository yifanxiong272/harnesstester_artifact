# file: browser_use/browser/session.py:1420-1506
# asked: {"lines": [1442, 1443, 1444, 1445, 1449, 1450, 1456, 1459, 1460, 1461, 1462, 1463, 1464, 1466, 1468, 1472, 1473, 1477, 1479, 1480, 1482, 1484, 1485, 1486, 1490, 1491, 1492, 1493, 1497, 1498, 1499, 1500, 1501, 1503, 1504, 1506], "branches": [[1440, 1442], [1443, 1444], [1443, 1449], [1454, 1456], [1459, 1460], [1459, 1466], [1462, 1459], [1462, 1463], [1466, 1468], [1466, 1471], [1472, 1473], [1472, 1477], [1477, 1479], [1477, 1497], [1482, 1484], [1482, 1490], [1497, 1498], [1497, 1506]]}
# gained: {"lines": [1442, 1443, 1444, 1445, 1456, 1459, 1460, 1461, 1462, 1463, 1464, 1466, 1468, 1472, 1473, 1477, 1479, 1480, 1482, 1484, 1485, 1486, 1490, 1491, 1492, 1493, 1497, 1498, 1499, 1500, 1501, 1503, 1504, 1506], "branches": [[1440, 1442], [1443, 1444], [1454, 1456], [1459, 1460], [1459, 1466], [1462, 1459], [1462, 1463], [1466, 1468], [1466, 1471], [1472, 1473], [1472, 1477], [1477, 1479], [1482, 1484], [1482, 1490], [1497, 1498]]}

import asyncio
import pytest

from browser_use.browser.session import BrowserSession
from cdp_use.cdp.target import TargetID


class DummyTarget:
    def __init__(self, target_type: str):
        self.target_type = target_type


class DummySession:
    def __init__(self, session_id="sess-1"):
        self.session_id = session_id
        # build cdp_client with required chain: cdp_client.send.Runtime.runIfWaitingForDebugger
        class _Runtime:
            @staticmethod
            async def runIfWaitingForDebugger(session_id=None):
                return "resumed"

        class _Send:
            Runtime = _Runtime

        class _CDPClient:
            send = _Send()

        self.cdp_client = _CDPClient()


class DummySessionManager:
    def __init__(self):
        # control variables for behaviors
        self._ensure_focus_result = True
        self._get_session_calls = []
        self._session_to_return = None
        self._validate_session_result = True
        self._target_map = {}

    async def ensure_valid_focus(self, timeout=5.0):
        return self._ensure_focus_result

    def _get_session_for_target(self, target_id: TargetID | None):
        # record calls
        self._get_session_calls.append(target_id)
        return self._session_to_return

    async def validate_session(self, target_id: TargetID):
        return self._validate_session_result

    def get_target(self, target_id: TargetID):
        return self._target_map.get(target_id)


@pytest.mark.asyncio
async def test_get_or_create_with_no_focus_raises(monkeypatch):
    session = BrowserSession()
    # ensure cdp root set and session_manager present
    session._cdp_client_root = object()
    mgr = DummySessionManager()
    mgr._ensure_focus_result = False
    session.session_manager = mgr

    with pytest.raises(ValueError) as exc:
        await session.get_or_create_cdp_session(target_id=None)
    assert "No valid agent focus available" in str(exc.value)


@pytest.mark.asyncio
async def test_waits_for_attach_then_sets_focus_for_page(monkeypatch):
    session = BrowserSession()
    session._cdp_client_root = object()
    mgr = DummySessionManager()
    # simulate initial missing session, then appearing
    call_count = {"calls": 0}

    real_session = DummySession(session_id="target-1234")
    # create _get_session_for_target that returns None first time, then returns real_session
    def get_session_once(target_id):
        call_count["calls"] += 1
        if call_count["calls"] >= 2:
            return real_session
        return None

    mgr._get_session_for_target = get_session_once
    mgr._validate_session_result = True
    mgr._target_map["target-1234"] = DummyTarget("page")
    session.session_manager = mgr

    # ensure agent focus different so update occurs
    session.agent_focus_target_id = "old-focus"

    # capture original sleep to avoid recursion
    original_sleep = asyncio.sleep

    async def fast_sleep(delay):
        # use original sleep so we don't recurse into patched function
        await original_sleep(0)

    monkeypatch.setattr(
        "browser_use.browser.session.asyncio.sleep", fast_sleep
    )

    got = await session.get_or_create_cdp_session(target_id="target-1234", focus=True)
    assert got is real_session
    assert session.agent_focus_target_id == "target-1234"


@pytest.mark.asyncio
async def test_wait_for_attach_times_out_raises(monkeypatch):
    session = BrowserSession()
    session._cdp_client_root = object()
    mgr = DummySessionManager()
    # never return a session
    mgr._session_to_return = None
    session.session_manager = mgr

    # capture original sleep to avoid recursion
    original_sleep = asyncio.sleep

    async def fast_sleep(delay):
        await original_sleep(0)

    monkeypatch.setattr(
        "browser_use.browser.session.asyncio.sleep", fast_sleep
    )

    with pytest.raises(ValueError) as exc:
        await session.get_or_create_cdp_session(target_id="missing-target", focus=False)
    assert "Target missing-target not found" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_session_failure_raises(monkeypatch):
    session = BrowserSession()
    session._cdp_client_root = object()
    mgr = DummySessionManager()
    # return a session immediately
    real_session = DummySession(session_id="tgt-xyz")
    mgr._session_to_return = real_session
    mgr._validate_session_result = False
    session.session_manager = mgr

    with pytest.raises(ValueError) as exc:
        await session.get_or_create_cdp_session(target_id="tgt-xyz", focus=False)
    assert "has detached - no active sessions" in str(exc.value)


@pytest.mark.asyncio
async def test_ignore_focus_for_non_page_and_handle_run_if_waiting_exceptions(monkeypatch):
    session = BrowserSession()
    session._cdp_client_root = object()
    mgr = DummySessionManager()
    # return session immediately
    real_session = DummySession(session_id="tgt-iframe")
    # override cdp client's runIfWaitingForDebugger to raise
    async def raising_runIfWaitingForDebugger(session_id=None):
        raise RuntimeError("not waiting")
    # attach raising method
    class _Runtime2:
        @staticmethod
        async def runIfWaitingForDebugger(session_id=None):
            return await raising_runIfWaitingForDebugger(session_id)

    class _Send2:
        Runtime = _Runtime2

    class _CDPClient2:
        send = _Send2()

    real_session.cdp_client = _CDPClient2()

    mgr._session_to_return = real_session
    mgr._validate_session_result = True
    mgr._target_map["tgt-iframe"] = DummyTarget("iframe")
    session.session_manager = mgr

    # set an existing focus so it stays unchanged after ignored focus request
    session.agent_focus_target_id = "existing-focus"

    got = await session.get_or_create_cdp_session(target_id="tgt-iframe", focus=True)
    assert got is real_session
    # focus should remain unchanged because target type is iframe
    assert session.agent_focus_target_id == "existing-focus"
