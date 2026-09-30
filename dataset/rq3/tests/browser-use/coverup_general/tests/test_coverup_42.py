# file: browser_use/browser/session_manager.py:750-844
# asked: {"lines": [759, 760, 763, 764, 766, 769, 773, 774, 775, 777, 779, 780, 781, 782, 783, 788, 790, 792, 793, 794, 795, 796, 797, 798, 800, 801, 802, 805, 807, 808, 809, 811, 814, 815, 818, 820, 821, 823, 824, 825, 826, 827, 828, 830, 831, 832, 835, 836, 837, 840, 841, 842, 843, 844], "branches": [[773, 774], [773, 788], [792, 793], [794, 795], [794, 807], [796, 794], [796, 797], [800, 801], [800, 805], [801, 794], [801, 802], [807, 808], [807, 811], [824, 825], [824, 836], [826, 824], [826, 827], [830, 831], [830, 835], [831, 824], [831, 832]]}
# gained: {"lines": [759, 760, 763, 764, 766, 769, 773, 774, 775, 777, 779, 780, 781, 782, 783, 788, 790, 792, 793, 794, 795, 796, 797, 798, 800, 801, 802, 807, 808, 809, 814, 815, 818, 820, 821, 823, 824, 825, 826, 836, 837, 840, 841, 842, 843, 844], "branches": [[773, 774], [773, 788], [792, 793], [794, 795], [794, 807], [796, 797], [800, 801], [801, 802], [807, 808], [824, 825], [824, 836], [826, 824]]}

import asyncio
import types
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


class DummyTargetObj:
    def __init__(self, target_type):
        self.target_type = target_type


class DummySession:
    def __init__(self, lifecycle_events=None):
        self._lifecycle_events = lifecycle_events


class DummyTargetAPI:
    def __init__(self, targets, fail_attach_for=None):
        # targets: list of dicts with 'targetId' and optional 'type'
        self._targets = targets
        self._fail_attach_for = set(fail_attach_for or ())

    async def getTargets(self):
        # emulate cdp response
        return {'targetInfos': list(self._targets)}

    async def attachToTarget(self, params=None):
        tid = params.get('targetId')
        # emulate attach success or failure
        if tid in self._fail_attach_for:
            raise Exception("attach failed")
        return {'sessionId': f'session-{tid}'}


class DummyCDPClientRoot:
    def __init__(self, targets, fail_attach_for=None):
        self.send = types.SimpleNamespace(Target=DummyTargetAPI(targets, fail_attach_for=fail_attach_for))


@pytest.mark.asyncio
async def test_initialize_existing_targets_attaches_and_counts_ready(monkeypatch):
    """
    Test the successful path: one page target with a session that has lifecycle events
    should be counted as ready and the ready_event should be set, so await succeeds.
    Also ensure attachToTarget exception branch is exercised for another target.
    """
    # Prepare targets: one page (t-page) and one other (t-other)
    targets = [{'targetId': 't-page', 'type': 'page'}, {'targetId': 't-other', 'type': 'other'}]
    # Simulate attach failure for t-other to hit exception logging branch
    cdp_root = DummyCDPClientRoot(targets, fail_attach_for=['t-other'])

    # Prepare browser_session stub
    browser_session = types.SimpleNamespace(_cdp_client_root=cdp_root, logger=DummyLogger())

    manager = SessionManager(browser_session)
    # Prepare internal state: we will have a session for 't-page' immediately
    manager._targets['t-page'] = DummyTargetObj('page')
    manager._targets['t-other'] = DummyTargetObj('other')
    # Return a session that has lifecycle events (non-None) for the page target
    def fake_get_session_for_target(tid):
        if tid == 't-page':
            return DummySession(lifecycle_events={'something': True})
        if tid == 't-other':
            return DummySession()  # non-page; should be counted even without lifecycle events
        return None
    monkeypatch.setattr(manager, '_get_session_for_target', fake_get_session_for_target)

    # Patch create_task_with_error_handling to actually create a background task
    def fake_create_task_with_error_handling(coro, name=None, logger_instance=None):
        return asyncio.create_task(coro)
    monkeypatch.setattr(sm_mod, 'create_task_with_error_handling', fake_create_task_with_error_handling)

    # Run the initializer - should complete without timing out
    await manager._initialize_existing_targets()

    # Assertions:
    # - attachToTarget should have been attempted; for t-other it failed and should have logged a debug
    dbg = browser_session.logger.debug_messages
    assert any('Discovered' in m or 'Failed to attach to existing target' in m for m in dbg)
    # - No timeout warnings
    assert browser_session.logger.warning_messages == []


@pytest.mark.asyncio
async def test_initialize_existing_targets_timeout_path(monkeypatch):
    """
    Test the timeout path: no sessions are ready -> the wait_for should timeout,
    warning should be emitted, and check_task should be cancelled and awaited.
    """
    # Prepare targets: two targets
    targets = [{'targetId': 't1', 'type': 'page'}, {'targetId': 't2', 'type': 'other'}]
    cdp_root = DummyCDPClientRoot(targets, fail_attach_for=[])

    browser_session = types.SimpleNamespace(_cdp_client_root=cdp_root, logger=DummyLogger())
    manager = SessionManager(browser_session)

    # manager._targets left empty or with types but _get_session_for_target returns None to force timeout
    manager._targets['t1'] = DummyTargetObj('page')
    manager._targets['t2'] = DummyTargetObj('other')

    def fake_get_session_for_target_none(tid):
        return None
    monkeypatch.setattr(manager, '_get_session_for_target', fake_get_session_for_target_none)

    # Patch create_task_with_error_handling to start the checking task
    def fake_create_task_with_error_handling(coro, name=None, logger_instance=None):
        return asyncio.create_task(coro)
    monkeypatch.setattr(sm_mod, 'create_task_with_error_handling', fake_create_task_with_error_handling)

    # Monkeypatch asyncio.wait_for to raise TimeoutError immediately to avoid waiting
    async def fake_wait_for(awaitable, timeout):
        raise TimeoutError
    monkeypatch.setattr(asyncio, 'wait_for', fake_wait_for)

    # Run initializer; this should hit the TimeoutError branch and log a warning
    await manager._initialize_existing_targets()

    # Assert that a warning was logged about initialization timeout
    warnings = browser_session.logger.warning_messages
    assert any('Initialization timeout' in w or 'Initialization timeout after' in w for w in warnings)
