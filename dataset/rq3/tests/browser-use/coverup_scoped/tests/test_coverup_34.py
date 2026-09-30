# file: browser_use/browser/session.py:3839-3895
# asked: {"lines": [3847, 3848, 3850, 3851, 3853, 3854, 3855, 3856, 3857, 3860, 3861, 3862, 3863, 3864, 3865, 3866, 3867, 3870, 3871, 3872, 3873, 3874, 3875, 3876, 3877, 3880, 3881, 3882, 3884, 3885, 3886, 3887, 3889, 3890, 3891, 3894, 3895], "branches": [[3847, 3848], [3847, 3860], [3851, 3853], [3851, 3860], [3860, 3861], [3860, 3870], [3870, 3871], [3870, 3880], [3880, 3881], [3880, 3894], [3885, 3886], [3885, 3889]]}
# gained: {"lines": [3847, 3848, 3850, 3851, 3853, 3854, 3855, 3856, 3857, 3860, 3861, 3862, 3863, 3864, 3865, 3870, 3871, 3872, 3873, 3874, 3875, 3880, 3881, 3882, 3884, 3885, 3886, 3887, 3889, 3890, 3891, 3894, 3895], "branches": [[3847, 3848], [3847, 3860], [3851, 3853], [3860, 3861], [3860, 3870], [3870, 3871], [3870, 3880], [3880, 3881], [3885, 3886]]}

import types
import asyncio
import logging
import pytest

from browser_use.browser import session as session_mod

# Helpers
class DummyTarget:
    def __init__(self, url):
        self.url = url


class DummyCDPSession:
    def __init__(self, target_id):
        self.target_id = target_id


def make_session_instance():
    # Use pydantic's construct to create an instance without validation,
    # then set attributes directly in __dict__ to avoid assignment validation.
    inst = session_mod.BrowserSession.construct()
    inst.__dict__['session_manager'] = None
    inst.__dict__['agent_focus_target_id'] = None
    # placeholders for async methods, can be replaced by tests
    async def default_get_or_create_cdp_session(target_id=None, focus=True):
        return DummyCDPSession(target_id or "main-target")
    async def default_cdp_client_for_frame(frame_id):
        return DummyCDPSession("frame-target")
    inst.__dict__['get_or_create_cdp_session'] = default_get_or_create_cdp_session
    inst.__dict__['cdp_client_for_frame'] = default_cdp_client_for_frame
    return inst


@pytest.mark.asyncio
async def test_cdp_client_for_node_uses_session_id_and_logs_debug(caplog):
    caplog.set_level(logging.DEBUG)
    inst = make_session_instance()

    # Node with session_id set
    node = types.SimpleNamespace(session_id="sess-1", frame_id=None, target_id=None, backend_node_id=111)

    # session_manager that returns a CDPSession and a Target
    class SM:
        def get_session(self, sid):
            assert sid == "sess-1"
            return DummyCDPSession("target-1")

        def get_target(self, tid):
            assert tid == "target-1"
            return DummyTarget("https://example.com/sess")

    inst.__dict__['session_manager'] = SM()

    result = await session_mod.BrowserSession.cdp_client_for_node(inst, node)
    assert isinstance(result, DummyCDPSession)
    assert result.target_id == "target-1"

    # ensure debug log was produced and contains the URL
    assert any("Using session from node.session_id" in rec.getMessage() for rec in caplog.records)
    assert any("https://example.com/sess" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_session_id_get_session_raises_then_frame_id_used(caplog):
    caplog.set_level(logging.DEBUG)
    inst = make_session_instance()

    # Node with session_id and frame_id set (session_id will raise)
    node = types.SimpleNamespace(session_id="bad-sess", frame_id="frame-42", target_id=None, backend_node_id=222)

    # session_manager that raises on get_session but provides get_target for frame result
    class SM:
        def get_session(self, sid):
            raise RuntimeError("session lookup failed")

        def get_target(self, tid):
            assert tid == "frame-target"
            return DummyTarget("https://example.com/frame")

    inst.__dict__['session_manager'] = SM()

    # cdp_client_for_frame returns a DummyCDPSession with target_id "frame-target"
    async def c_for_frame(frame_id):
        assert frame_id == "frame-42"
        return DummyCDPSession("frame-target")
    inst.__dict__['cdp_client_for_frame'] = c_for_frame

    result = await session_mod.BrowserSession.cdp_client_for_node(inst, node)
    assert isinstance(result, DummyCDPSession)
    assert result.target_id == "frame-target"

    # ensure a debug about failure was logged and a debug about using frame session was logged
    assert any("Failed to get session by session_id" in rec.getMessage() for rec in caplog.records)
    assert any("Using session from node.frame_id" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_target_id_branch_uses_get_or_create_and_logs_debug(caplog):
    caplog.set_level(logging.DEBUG)
    inst = make_session_instance()

    node = types.SimpleNamespace(session_id=None, frame_id=None, target_id="t-999", backend_node_id=333)

    # session_manager providing target info
    class SM:
        def get_target(self, tid):
            assert tid == "t-999"
            return DummyTarget("https://example.com/target")
    inst.__dict__['session_manager'] = SM()

    async def get_or_create(target_id=None, focus=True):
        assert target_id == "t-999"
        assert focus is False  # per code it should pass focus=False for this branch
        return DummyCDPSession("t-999")
    inst.__dict__['get_or_create_cdp_session'] = get_or_create

    result = await session_mod.BrowserSession.cdp_client_for_node(inst, node)
    assert isinstance(result, DummyCDPSession)
    assert result.target_id == "t-999"
    assert any("Using session from node.target_id" in rec.getMessage() for rec in caplog.records)
    assert any("https://example.com/target" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_agent_focus_used_and_warning_logged_then_value_error_falls_back_to_main_session(caplog):
    caplog.set_level(logging.DEBUG)
    # Part A: agent_focus works and logs a warning
    inst = make_session_instance()

    node = types.SimpleNamespace(session_id=None, frame_id=None, target_id=None, backend_node_id=444)

    class SM:
        def get_target(self, tid):
            assert tid == "agent-t"
            return DummyTarget("https://example.com/agent")
    inst.__dict__['session_manager'] = SM()
    inst.__dict__['agent_focus_target_id'] = "agent-t"

    async def get_or_create_agent(tid=None, focus=True):
        # Called with target_id and focus=False according to code
        assert tid == "agent-t"
        assert focus is False
        return DummyCDPSession("agent-t")
    inst.__dict__['get_or_create_cdp_session'] = get_or_create_agent

    caplog.clear()
    result = await session_mod.BrowserSession.cdp_client_for_node(inst, node)
    assert isinstance(result, DummyCDPSession)
    assert result.target_id == "agent-t"
    # should have emitted a warning mentioning agent target url
    assert any("Using agent_focus session" in rec.getMessage() for rec in caplog.records)
    assert any("https://example.com/agent" in rec.getMessage() for rec in caplog.records)

    # Part B: agent_focus get_or_create raises ValueError -> fallback to main session and error logged
    inst2 = make_session_instance()
    node2 = types.SimpleNamespace(session_id=None, frame_id=None, target_id=None, backend_node_id=555)

    class SM2:
        def get_target(self, tid):
            assert tid == "agent-t2"
            return DummyTarget("https://example.com/agent2")
    inst2.__dict__['session_manager'] = SM2()
    inst2.__dict__['agent_focus_target_id'] = "agent-t2"

    async def get_or_create_raise(tid=None, focus=True):
        # simulate ValueError when trying to use agent focus session
        if tid == "agent-t2":
            raise ValueError("cannot create agent session")
        # fallback main session (no tid) should return main-session
        return DummyCDPSession("main-session")
    inst2.__dict__['get_or_create_cdp_session'] = get_or_create_raise

    caplog.clear()
    result2 = await session_mod.BrowserSession.cdp_client_for_node(inst2, node2)
    assert isinstance(result2, DummyCDPSession)
    assert result2.target_id == "main-session"
    # error should be logged because no session info and used main session
    assert any("No session info for node" in rec.getMessage() for rec in caplog.records)
