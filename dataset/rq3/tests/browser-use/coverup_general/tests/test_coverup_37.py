# file: browser_use/cli.py:1611-1725
# asked: {"lines": [1611, 1614, 1616, 1619, 1621, 1622, 1623, 1626, 1627, 1628, 1630, 1633, 1634, 1636, 1638, 1639, 1640, 1641, 1642, 1644, 1648, 1650, 1651, 1652, 1654, 1657, 1658, 1660, 1661, 1662, 1663, 1666, 1667, 1668, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1680, 1681, 1683, 1684, 1686, 1687, 1688, 1689, 1690, 1691, 1692, 1693, 1695, 1696, 1697, 1699, 1700, 1701, 1708, 1711, 1712, 1713, 1714, 1716, 1718, 1720, 1721, 1722, 1725], "branches": [[1622, 1623], [1622, 1626], [1639, 1640], [1639, 1641], [1641, 1642], [1641, 1644]]}
# gained: {"lines": [1611, 1614, 1616, 1619, 1621, 1622, 1623, 1626, 1627, 1628, 1630, 1633, 1634, 1636, 1638, 1639, 1640, 1641, 1642, 1644, 1648, 1650, 1651, 1652, 1654, 1657, 1658, 1660, 1661, 1662, 1663, 1671, 1672, 1673, 1674, 1680, 1681, 1683, 1684, 1686, 1687, 1688, 1689, 1690, 1695, 1696, 1697, 1699, 1700, 1701, 1708, 1711, 1712, 1713, 1714, 1716, 1718, 1720, 1721, 1722, 1725], "branches": [[1622, 1623], [1622, 1626], [1639, 1640], [1639, 1641], [1641, 1642], [1641, 1644]]}

import sys
import types
import asyncio
import pytest

import importlib


@pytest.mark.asyncio
async def test_textual_interface_success_with_setup_log_pipes(monkeypatch):
    # Import the module under test
    cli = importlib.import_module("browser_use.cli")

    # Prepare fakes
    class FakeBrowserProfile:
        def __init__(self, user_data_dir, **kwargs):
            self.user_data_dir = user_data_dir
            self.kwargs = kwargs

    class FakeBrowserSession:
        def __init__(self, browser_profile):
            self.browser_profile = browser_profile
            self.id = "session-FAKE-1234"

    class FakeController:
        def __init__(self):
            self.initialized = True

    class FakeLLM:
        def __init__(self):
            self.model_name = "fake-model"
            self.temperature = 0.1

    setup_called = {}

    def fake_setup_log_pipes(session_id):
        setup_called['session_id'] = session_id

    class FakeBrowserUseApp:
        def __init__(self, config):
            self.config = config
            self.run_async_called = False
            self.browser_session = None
            self.controller = None
            self.llm = None

        async def run_async(self):
            # simulate a short async operation
            await asyncio.sleep(0)
            self.run_async_called = True
            return None

    # Monkeypatch constants and classes in cli module
    monkeypatch.setattr(cli, "USER_DATA_DIR", "/tmp/fake_userdata", raising=False)
    monkeypatch.setattr(cli, "BrowserProfile", FakeBrowserProfile, raising=False)
    monkeypatch.setattr(cli, "BrowserSession", FakeBrowserSession, raising=False)
    monkeypatch.setattr(cli, "Controller", FakeController, raising=False)
    monkeypatch.setattr(cli, "get_llm", lambda config: FakeLLM(), raising=False)
    monkeypatch.setattr(cli, "BrowserUseApp", FakeBrowserUseApp, raising=False)

    # Inject a fake browser_use.logging_config module with setup_log_pipes
    mod = types.ModuleType("browser_use.logging_config")
    mod.setup_log_pipes = fake_setup_log_pipes
    monkeypatch.setitem(sys.modules, "browser_use.logging_config", mod)

    # Build config with executable_path and headless True to hit both logging branches
    config = {"browser": {"executable_path": "/fake/bin", "headless": True}, "model": {"name": "m1"}}

    # Ensure environment var is not interfering initially
    monkeypatch.delenv("BROWSER_USE_SETUP_LOGGING", raising=False)

    # Run the textual_interface coroutine
    await cli.textual_interface(config)

    # Assertions: setup_log_pipes should have been called with session id
    assert setup_called.get("session_id") == "session-FAKE-1234"

    # Ensure env var was set to 'false' during get_llm step (function sets it)
    assert cli.os.environ.get("BROWSER_USE_SETUP_LOGGING") == "false"


@pytest.mark.asyncio
async def test_textual_interface_setup_log_pipes_raises(monkeypatch):
    # Import the module under test
    cli = importlib.import_module("browser_use.cli")

    # Prepare fakes similar to previous test
    class FakeBrowserProfile:
        def __init__(self, user_data_dir, **kwargs):
            self.user_data_dir = user_data_dir
            self.kwargs = kwargs

    class FakeBrowserSession:
        def __init__(self, browser_profile):
            self.browser_profile = browser_profile
            self.id = "session-FAIL-0001"

    class FakeController:
        def __init__(self):
            self.initialized = True

    class FakeLLM:
        def __init__(self):
            self.model = "fallback-model"
            self.temperature = 0.2

    class FakeBrowserUseApp:
        def __init__(self, config):
            self.config = config
            self.run_async_called = False
            self.browser_session = None
            self.controller = None
            self.llm = None

        async def run_async(self):
            # simulate a short async operation
            await asyncio.sleep(0)
            self.run_async_called = True
            return None

    # Monkeypatch constants and classes in cli module
    monkeypatch.setattr(cli, "USER_DATA_DIR", "/tmp/fake_userdata2", raising=False)
    monkeypatch.setattr(cli, "BrowserProfile", FakeBrowserProfile, raising=False)
    monkeypatch.setattr(cli, "BrowserSession", FakeBrowserSession, raising=False)
    monkeypatch.setattr(cli, "Controller", FakeController, raising=False)
    monkeypatch.setattr(cli, "get_llm", lambda config: FakeLLM(), raising=False)
    monkeypatch.setattr(cli, "BrowserUseApp", FakeBrowserUseApp, raising=False)

    # Inject a fake browser_use.logging_config module whose setup_log_pipes raises
    mod = types.ModuleType("browser_use.logging_config")

    def raising_setup_log_pipes(session_id):
        raise RuntimeError("failed to create pipes")

    mod.setup_log_pipes = raising_setup_log_pipes
    monkeypatch.setitem(sys.modules, "browser_use.logging_config", mod)

    # Build config with headless False to hit visible logging branch
    config = {"browser": {"headless": False}, "model": {}}

    # Run the textual_interface coroutine; it should complete successfully
    await cli.textual_interface(config)

    # If completed, nothing was raised; ensure env var was set
    assert cli.os.environ.get("BROWSER_USE_SETUP_LOGGING") == "false"


@pytest.mark.asyncio
async def test_textual_interface_run_async_raises_propagates(monkeypatch):
    # Import module under test
    cli = importlib.import_module("browser_use.cli")

    # Prepare fakes
    class FakeBrowserProfile:
        def __init__(self, user_data_dir, **kwargs):
            self.user_data_dir = user_data_dir
            self.kwargs = kwargs

    class FakeBrowserSession:
        def __init__(self, browser_profile):
            self.browser_profile = browser_profile
            self.id = "session-RAISE-9999"

    class FakeController:
        def __init__(self):
            self.initialized = True

    class FakeLLM:
        def __init__(self):
            self.model_name = "err-model"
            self.temperature = 0.3

    class BadBrowserUseApp:
        def __init__(self, config):
            self.config = config
            self.browser_session = None
            self.controller = None
            self.llm = None

        async def run_async(self):
            await asyncio.sleep(0)
            raise ValueError("run failed")

    # Monkeypatch constants and classes
    monkeypatch.setattr(cli, "USER_DATA_DIR", "/tmp/fake_userdata3", raising=False)
    monkeypatch.setattr(cli, "BrowserProfile", FakeBrowserProfile, raising=False)
    monkeypatch.setattr(cli, "BrowserSession", FakeBrowserSession, raising=False)
    monkeypatch.setattr(cli, "Controller", FakeController, raising=False)
    monkeypatch.setattr(cli, "get_llm", lambda config: FakeLLM(), raising=False)
    monkeypatch.setattr(cli, "BrowserUseApp", BadBrowserUseApp, raising=False)

    # Provide a harmless logging_config so inner try does not error
    mod = types.ModuleType("browser_use.logging_config")
    mod.setup_log_pipes = lambda session_id: None
    monkeypatch.setitem(sys.modules, "browser_use.logging_config", mod)

    config = {"browser": {"headless": False}, "model": {"name": "x"}}

    # Expect the ValueError to propagate out of textual_interface
    with pytest.raises(ValueError, match="run failed"):
        await cli.textual_interface(config)
