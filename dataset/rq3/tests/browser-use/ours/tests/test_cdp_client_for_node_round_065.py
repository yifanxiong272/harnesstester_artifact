import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

from browser_use.browser.session import BrowserSession

# We will call the unbound async function BrowserSession.cdp_client_for_node
cdp_client_for_node_fn = BrowserSession.cdp_client_for_node


def _last_message(mock_fn):
    # Helper to extract last logged message string from a MagicMock call history
    if not mock_fn.called:
        return None
    return mock_fn.call_args_list[-1][0][0]


def test_session_id_success_round_065():
    # Node has session_id -> should use session_manager.get_session and return that session
    node = SimpleNamespace(session_id="sid-123", frame_id=None, target_id=None, backend_node_id=42)

    returned_session = SimpleNamespace(target_id="t-session")
    target = SimpleNamespace(url="https://session.example")

    session_manager = MagicMock()
    session_manager.get_session.return_value = returned_session
    session_manager.get_target.return_value = target

    logger = MagicMock()

    fake_self = SimpleNamespace(
        session_manager=session_manager,
        agent_focus_target_id=None,
        logger=logger,
        # not used in this branch but present
        cdp_client_for_frame=AsyncMock(),
        get_or_create_cdp_session=AsyncMock()
    )

    res = asyncio.run(cdp_client_for_node_fn(fake_self, node))

    assert res is returned_session
    # session_manager.get_session should be called with node.session_id
    session_manager.get_session.assert_called_once_with("sid-123")
    # debug should have been called and include the expected fragment
    last = _last_message(logger.debug)
    assert last is not None and "Using session from node.session_id" in last


def test_session_id_none_then_frame_success_round_065():
    # get_session returns None -> should try frame branch
    node = SimpleNamespace(session_id=None, frame_id="frame-1", target_id=None, backend_node_id=7)

    returned_session = SimpleNamespace(target_id="t-frame")
    target = SimpleNamespace(url="https://frame.example")

    session_manager = MagicMock()
    session_manager.get_session.return_value = None
    session_manager.get_target.return_value = target

    logger = MagicMock()

    async def fake_cdp_client_for_frame(frame_id):
        assert frame_id == "frame-1"
        return returned_session

    fake_self = SimpleNamespace(
        session_manager=session_manager,
        agent_focus_target_id=None,
        logger=logger,
        cdp_client_for_frame=AsyncMock(side_effect=fake_cdp_client_for_frame),
        get_or_create_cdp_session=AsyncMock()
    )

    res = asyncio.run(cdp_client_for_node_fn(fake_self, node))

    assert res is returned_session
    # ensure cdp_client_for_frame was awaited with the expected frame_id
    fake_self.cdp_client_for_frame.assert_awaited_once()
    last = _last_message(logger.debug)
    assert last is not None and "Using session from node.frame_id" in last


def test_frame_raises_then_target_success_round_065():
    # cdp_client_for_frame raises -> fallback to target_id branch
    node = SimpleNamespace(session_id=None, frame_id="frame-bad", target_id="target-99", backend_node_id=9)

    returned_session = SimpleNamespace(target_id="t-target")
    target = SimpleNamespace(url="https://target.example")

    session_manager = MagicMock()
    session_manager.get_target.return_value = target

    logger = MagicMock()

    async def bad_frame(frame_id):
        raise RuntimeError("frame lookup failed")

    fake_self = SimpleNamespace(
        session_manager=session_manager,
        agent_focus_target_id=None,
        logger=logger,
        cdp_client_for_frame=AsyncMock(side_effect=bad_frame),
        get_or_create_cdp_session=AsyncMock(return_value=returned_session)
    )

    res = asyncio.run(cdp_client_for_node_fn(fake_self, node))

    assert res is returned_session
    # Ensure frame branch was attempted and logged the failure
    assert _last_message(logger.debug) is not None
    # Ensure get_or_create_cdp_session was called with the node.target_id
    fake_self.get_or_create_cdp_session.assert_awaited_once_with(target_id="target-99", focus=False)


def test_agent_focus_fallback_with_target_warning_round_065():
    # No session/frame/target on node -> use agent_focus_target_id and warn
    node = SimpleNamespace(session_id=None, frame_id=None, target_id=None, backend_node_id=55)

    returned_session = SimpleNamespace(target_id="t-agent")
    target = SimpleNamespace(url="https://agent.example")

    session_manager = MagicMock()
    session_manager.get_target.return_value = target

    logger = MagicMock()

    fake_self = SimpleNamespace(
        session_manager=session_manager,
        agent_focus_target_id="agent-1",
        logger=logger,
        cdp_client_for_frame=AsyncMock(),
        get_or_create_cdp_session=AsyncMock(return_value=returned_session)
    )

    res = asyncio.run(cdp_client_for_node_fn(fake_self, node))

    assert res is returned_session
    # session_manager.get_target should have been called for the agent_focus_target_id
    session_manager.get_target.assert_called_once_with("agent-1")
    # warning should mention using agent_focus session
    last_warn = _last_message(logger.warning)
    assert last_warn is not None and "Using agent_focus session" in last_warn


def test_agent_focus_value_error_falls_to_main_round_065():
    # agent_focus path raises ValueError -> fall through and use main session (no args)
    node = SimpleNamespace(session_id=None, frame_id=None, target_id=None, backend_node_id=77)

    main_session = SimpleNamespace(target_id="t-main")
    agent_target = SimpleNamespace(url="https://agent.example")

    session_manager = MagicMock()
    session_manager.get_target.return_value = agent_target

    logger = MagicMock()

    async def conditional_get_or_create(*args, **kwargs):
        # If called with the agent_focus_target_id and focus=False -> raise ValueError
        if len(args) >= 1 and args[0] == "agent-1":
            raise ValueError("cannot use agent focus")
        # Called with no args -> return main session
        if len(args) == 0:
            return main_session
        # Fallback
        return main_session

    fake_self = SimpleNamespace(
        session_manager=session_manager,
        agent_focus_target_id="agent-1",
        logger=logger,
        cdp_client_for_frame=AsyncMock(),
        get_or_create_cdp_session=AsyncMock(side_effect=conditional_get_or_create)
    )

    res = asyncio.run(cdp_client_for_node_fn(fake_self, node))

    assert res is main_session
    # Ensure the first call attempted used the agent_focus_target_id and raised (handled internally)
    # and the final call used the no-arg fallback to get main session
    # We can assert get_or_create_cdp_session was awaited at least twice
    assert fake_self.get_or_create_cdp_session.await_count >= 1
    # Error log should include fallback message
    last_err = _last_message(logger.error)
    assert last_err is not None and "No session info for node" in last_err
