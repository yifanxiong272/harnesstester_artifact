import asyncio
from types import SimpleNamespace
import pytest

from browser_use.browser.session import BrowserSession


class FakeLogger:
    def __init__(self):
        self.debug_msgs = []
        self.error_msgs = []
        self.warning_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)

    def warning(self, msg):
        self.warning_msgs.append(msg)


def _make_cdp_session(nav_result, session_id="SID123", target_id="target-abc", lifecycle_events=None):
    # Build a minimal cdp_client structure with a Page.navigate coroutine
    async def navigate(params=None, session_id=None):
        return nav_result

    page = SimpleNamespace(navigate=navigate)
    send = SimpleNamespace(Page=page)
    cdp_client = SimpleNamespace(send=send)
    cdp_session = SimpleNamespace(cdp_client=cdp_client, session_id=session_id, target_id=target_id)
    if lifecycle_events is not None:
        cdp_session._lifecycle_events = lifecycle_events
    return cdp_session


def _make_session_object(cdp_session, target_url="http://example.com/path"):
    # Return a plain object (not a pydantic BrowserSession instance) to avoid BaseModel init/validation
    sess = SimpleNamespace()

    # session_manager with get_target() returning object with url attribute
    sess.session_manager = SimpleNamespace(get_target=lambda tid: SimpleNamespace(url=target_url))

    async def get_or_create_cdp_session(target_id, focus=False):
        return cdp_session

    sess.get_or_create_cdp_session = get_or_create_cdp_session
    sess.logger = FakeLogger()
    return sess


@pytest.mark.asyncio
async def test_commit_early_return_round_026():
    """If wait_until == 'commit' the method should return early and log commit debug message."""
    nav_result = {"loaderId": "L1"}
    cdp_session = _make_cdp_session(nav_result=nav_result, lifecycle_events=[{"name": "load", "loaderId": "L1"}])
    sess = _make_session_object(cdp_session, target_url="http://otherdomain.com/path")

    # Call with timeout explicitly None to exercise same_domain logic path
    await BrowserSession._navigate_and_wait(sess, url="http://somedomain.com/", target_id="target-abc", timeout=None, wait_until="commit", nav_timeout=None)

    # Confirm the logger recorded a commit-ready message
    assert any(("commit" in m and "Page ready for" in m) for m in sess.logger.debug_msgs), sess.logger.debug_msgs


@pytest.mark.asyncio
async def test_nav_timeout_raises_round_026(monkeypatch):
    """Simulate asyncio.wait_for raising TimeoutError to exercise the Page.navigate timeout path."""
    nav_result = {"loaderId": "L2"}
    cdp_session = _make_cdp_session(nav_result=nav_result)
    sess = _make_session_object(cdp_session)

    # Force asyncio.wait_for to raise TimeoutError deterministically
    def fake_wait_for(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    with pytest.raises(RuntimeError) as excinfo:
        await BrowserSession._navigate_and_wait(sess, url="http://x", target_id="target-abc", timeout=1.0, wait_until="load", nav_timeout=None)

    # Expect the raised RuntimeError to mention the Page.navigate timeout and the nav_timeout (defaulted to 20.0)
    assert "Page.navigate() timed out after" in str(excinfo.value)
    assert "20.0s" in str(excinfo.value)


@pytest.mark.asyncio
async def test_nav_errorText_raises_round_026():
    """If Page.navigate returns errorText the method should raise a RuntimeError mentioning that text."""
    nav_result = {"errorText": "boom error"}
    cdp_session = _make_cdp_session(nav_result=nav_result)
    sess = _make_session_object(cdp_session)

    with pytest.raises(RuntimeError) as excinfo:
        await BrowserSession._navigate_and_wait(sess, url="http://x", target_id="target-abc", timeout=1.0, wait_until="load", nav_timeout=5.0)

    assert "Navigation failed: boom error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_missing_lifecycle_attr_round_026():
    """If cdp_session lacks _lifecycle_events attribute the method should raise a RuntimeError indicating monitoring not enabled."""
    nav_result = {"loaderId": "L3"}
    # Do not supply lifecycle_events to produce missing attribute
    cdp_session = _make_cdp_session(nav_result=nav_result)
    sess = _make_session_object(cdp_session)

    with pytest.raises(RuntimeError) as excinfo:
        await BrowserSession._navigate_and_wait(sess, url="http://x", target_id="target-abc", timeout=1.0, wait_until="load", nav_timeout=5.0)

    assert "Lifecycle monitoring not enabled" in str(excinfo.value)


@pytest.mark.asyncio
async def test_lifecycle_event_success_round_026():
    """Provide lifecycle events including an acceptable 'load' event and ensure the function returns and logs readiness."""
    lifecycle_events = [
        {"name": "load", "loaderId": "loader-main"},
        {"name": "networkIdle", "loaderId": "other-loader"},
    ]
    nav_result = {"loaderId": "loader-main"}
    cdp_session = _make_cdp_session(nav_result=nav_result, lifecycle_events=lifecycle_events)
    sess = _make_session_object(cdp_session)

    await BrowserSession._navigate_and_wait(sess, url="http://x", target_id="target-abc", timeout=2.0, wait_until="load", nav_timeout=5.0)

    # Should have logged a ready message referencing the 'load' event
    assert any(("Page ready for" in m and "load" in m) for m in sess.logger.debug_msgs), sess.logger.debug_msgs


@pytest.mark.asyncio
async def test_no_events_error_logged_round_026():
    """When timeout elapses and no lifecycle events were seen, error() should be called on the logger."""
    nav_result = {"loaderId": None}
    cdp_session = _make_cdp_session(nav_result=nav_result, lifecycle_events=[])
    sess = _make_session_object(cdp_session)

    # Use timeout 0 so the polling while loop is skipped deterministically
    await BrowserSession._navigate_and_wait(sess, url="http://x", target_id="target-abc", timeout=0, wait_until="load", nav_timeout=5.0)

    assert any("No lifecycle events received" in m for m in sess.logger.error_msgs), sess.logger.error_msgs
