# file: browser_use/cli.py:1611-1725
# asked: {"lines": [1611, 1614, 1616, 1619, 1621, 1622, 1623, 1626, 1627, 1628, 1630, 1633, 1634, 1636, 1638, 1639, 1640, 1641, 1642, 1644, 1648, 1650, 1651, 1652, 1654, 1657, 1658, 1660, 1661, 1662, 1663, 1666, 1667, 1668, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1680, 1681, 1683, 1684, 1686, 1687, 1688, 1689, 1690, 1691, 1692, 1693, 1695, 1696, 1697, 1699, 1700, 1701, 1708, 1711, 1712, 1713, 1714, 1716, 1718, 1720, 1721, 1722, 1725], "branches": [[1622, 1623], [1622, 1626], [1639, 1640], [1639, 1641], [1641, 1642], [1641, 1644]]}
# gained: {"lines": [1611, 1614, 1616, 1619, 1621, 1622, 1623, 1626, 1627, 1628, 1630, 1633, 1634, 1636, 1638, 1639, 1640, 1641, 1642, 1644, 1648, 1650, 1651, 1652, 1654, 1657, 1658, 1660, 1661, 1666, 1667, 1668, 1671, 1672, 1673, 1674, 1680, 1681, 1683, 1684, 1686, 1687, 1688, 1689, 1690, 1691, 1692, 1693, 1695, 1696, 1697, 1699, 1700, 1701, 1708, 1711, 1712, 1713, 1714, 1716, 1718, 1720, 1721, 1722, 1725], "branches": [[1622, 1623], [1622, 1626], [1639, 1640], [1639, 1641], [1641, 1642], [1641, 1644]]}

import sys
import types
import asyncio
import pathlib
import pytest

from browser_use import cli as cli_module


class FakeProfile:
    def __init__(self, user_data_dir, **kwargs):
        self.user_data_dir = user_data_dir
        self.kwargs = kwargs


class FakeSession:
    def __init__(self, *, browser_profile):
        # emulate an id attribute used by textual_interface
        self.id = "session-FAKE-1234"
        self.browser_profile = browser_profile
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeController:
    def __init__(self):
        self.initted = True


class SimpleLLM:
    def __init__(self, model_name="gpt-fake", temperature=0.2):
        self.model_name = model_name
        self.temperature = temperature


class FakeApp:
    def __init__(self, config):
        self.config = config
        self.browser_session = None
        self.controller = None
        self.llm = None
        self.ran = False

    async def run_async(self):
        # simple successful run
        self.ran = True


@pytest.mark.asyncio
async def test_textual_interface_success_with_setup_log_pipes(monkeypatch, tmp_path):
    """
    Test the normal successful path where browser/session/controller/llm/app
    initialize correctly and the logging_config.setup_log_pipes import succeeds.
    This should exercise branches that log executable_path and headless True.
    """
    # Prepare config with browser executable_path and headless True
    config = {
        "browser": {"executable_path": "/fake/bin/chrome", "headless": True},
        "model": {"name": "test-model"},
    }

    # Replace USER_DATA_DIR to avoid relying on real environment
    monkeypatch.setattr(cli_module, "USER_DATA_DIR", tmp_path)

    # Patch BrowserProfile and BrowserSession to our fakes
    monkeypatch.setattr(cli_module, "BrowserProfile", FakeProfile)
    monkeypatch.setattr(cli_module, "BrowserSession", FakeSession)

    # Ensure Controller is our fake
    monkeypatch.setattr(cli_module, "Controller", FakeController)

    # Track that get_llm is called and return a simple LLM object
    called = {}

    def fake_get_llm(cfg):
        called['cfg'] = cfg
        return SimpleLLM(model_name="fake-model", temperature=0.5)

    monkeypatch.setattr(cli_module, "get_llm", fake_get_llm)

    # Provide a logging_config module with setup_log_pipes that records session_id
    logmod = types.SimpleNamespace()
    called_sessions = []

    def setup_log_pipes(session_id):
        called_sessions.append(session_id)

    logmod.setup_log_pipes = setup_log_pipes
    monkeypatch.setitem(sys.modules, "browser_use.logging_config", logmod)

    # Use our FakeApp and ensure run_async runs successfully
    monkeypatch.setattr(cli_module, "BrowserUseApp", FakeApp)

    # Now call textual_interface
    await cli_module.textual_interface(config)

    # Assertions: get_llm was called with the config and setup_log_pipes got the session id
    assert called.get("cfg") is config
    assert called_sessions, "setup_log_pipes should have been called"
    # Ensure the recorded session id matches FakeSession.id tail
    assert called_sessions[0].endswith("1234")


@pytest.mark.asyncio
async def test_textual_interface_no_logging_config_and_app_raises(monkeypatch, tmp_path):
    """
    Test path where browser_use.logging_config is absent (import fails),
    and app.run_async raises an exception which should propagate from textual_interface.
    Also exercises the 'visible' branch (headless False).
    """
    config = {"browser": {"headless": False}, "model": {}}

    monkeypatch.setattr(cli_module, "USER_DATA_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "BrowserProfile", FakeProfile)
    monkeypatch.setattr(cli_module, "BrowserSession", FakeSession)
    monkeypatch.setattr(cli_module, "Controller", FakeController)

    def fake_get_llm(cfg):
        return SimpleLLM(model_name=None, temperature=0.0)

    monkeypatch.setattr(cli_module, "get_llm", fake_get_llm)

    # Ensure no browser_use.logging_config in sys.modules to force import failure
    if "browser_use.logging_config" in sys.modules:
        monkeypatch.delitem(sys.modules, "browser_use.logging_config", raising=False)

    # Create an app whose run_async raises
    class FailingApp(FakeApp):
        async def run_async(self):
            raise RuntimeError("app runtime failure")

    monkeypatch.setattr(cli_module, "BrowserUseApp", FailingApp)

    with pytest.raises(RuntimeError) as exc:
        await cli_module.textual_interface(config)
    assert "app runtime failure" in str(exc.value)


@pytest.mark.asyncio
async def test_textual_interface_browser_session_init_raises(monkeypatch, tmp_path):
    """
    Test that if BrowserSession initialization raises, textual_interface
    wraps and raises a RuntimeError indicating failed initialization.
    """
    config = {"browser": {}, "model": {}}

    monkeypatch.setattr(cli_module, "USER_DATA_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "BrowserProfile", FakeProfile)

    # Make BrowserSession raise on instantiation
    class BrokenSession:
        def __init__(self, *args, **kwargs):
            raise ValueError("no browser available")

    monkeypatch.setattr(cli_module, "BrowserSession", BrokenSession)
    # Controller shouldn't be reached but set it to normal to avoid other failures
    monkeypatch.setattr(cli_module, "Controller", FakeController)
    # Make get_llm normal in case it is reached
    monkeypatch.setattr(cli_module, "get_llm", lambda cfg: SimpleLLM())
    monkeypatch.setattr(cli_module, "BrowserUseApp", FakeApp)

    with pytest.raises(RuntimeError) as exc:
        await cli_module.textual_interface(config)
    assert "Failed to initialize BrowserSession" in str(exc.value)


@pytest.mark.asyncio
async def test_textual_interface_get_llm_raises(monkeypatch, tmp_path):
    """
    Test that if get_llm raises, textual_interface wraps and raises a RuntimeError.
    """
    config = {"browser": {}, "model": {}}

    monkeypatch.setattr(cli_module, "USER_DATA_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "BrowserProfile", FakeProfile)
    monkeypatch.setattr(cli_module, "BrowserSession", FakeSession)
    monkeypatch.setattr(cli_module, "Controller", FakeController)

    # get_llm raises
    def raising_get_llm(cfg):
        raise RuntimeError("llm backend error")

    monkeypatch.setattr(cli_module, "get_llm", raising_get_llm)
    monkeypatch.setattr(cli_module, "BrowserUseApp", FakeApp)

    with pytest.raises(RuntimeError) as exc:
        await cli_module.textual_interface(config)
    assert "Failed to initialize LLM" in str(exc.value)
