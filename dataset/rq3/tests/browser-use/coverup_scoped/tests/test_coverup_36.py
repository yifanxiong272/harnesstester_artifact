# file: browser_use/agent/service.py:1250-1306
# asked: {"lines": [1254, 1255, 1257, 1258, 1261, 1263, 1264, 1265, 1266, 1268, 1269, 1270, 1271, 1274, 1275, 1276, 1277, 1280, 1281, 1282, 1283, 1284, 1287, 1288, 1289, 1290, 1291, 1294, 1295, 1297, 1299, 1300, 1302, 1304, 1305, 1306], "branches": [[1254, 1255], [1254, 1261], [1261, 1263], [1261, 1287], [1263, 1264], [1263, 1280], [1274, 1275], [1274, 1280], [1280, 1281], [1280, 1287], [1297, 1299], [1297, 1302]]}
# gained: {"lines": [1254, 1255, 1257, 1258, 1261, 1263, 1264, 1265, 1266, 1268, 1269, 1274, 1275, 1276, 1277, 1280, 1281, 1282, 1283, 1284, 1287, 1288, 1289, 1290, 1291, 1294, 1295, 1297, 1299, 1300, 1304, 1305, 1306], "branches": [[1254, 1255], [1254, 1261], [1261, 1263], [1261, 1287], [1263, 1264], [1263, 1280], [1274, 1275], [1280, 1281], [1297, 1299]]}

import asyncio
import logging
from types import SimpleNamespace

import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import ActionResult, AgentError


class FakeLogger:
    def __init__(self, debug_enabled=False):
        self.calls = []
        self._debug_enabled = debug_enabled

    def warning(self, msg):
        self.calls.append(("warning", msg))

    def info(self, msg):
        self.calls.append(("info", msg))

    def log(self, level, msg):
        self.calls.append(("log", level, msg))

    def isEnabledFor(self, level):
        if level == logging.DEBUG:
            return self._debug_enabled
        return True


class TestAgent(Agent):
    # override logger property to allow assignment without running Agent.__init__
    @property
    def logger(self):
        return getattr(self, "_logger", None)

    @logger.setter
    def logger(self, value):
        self._logger = value

    # also override _demo_mode_log default to avoid relying on base implementation
    async def _demo_mode_log(self, message: str, level: str = "info", metadata: dict | None = None):
        # allow tests to replace this by setting attribute if needed
        func = getattr(self, "_demo_mode_log_override", None)
        if func:
            return await func(message, level, metadata)
        return None


@pytest.mark.asyncio
async def test_handle_step_error_interrupted():
    agent = object.__new__(TestAgent)
    # set attributes
    agent.logger = FakeLogger()
    agent.state = SimpleNamespace(consecutive_failures=0, last_result=None, stopped=False, n_steps=0)
    agent.settings = SimpleNamespace(max_failures=1, final_response_after_failure=False)
    agent.llm = SimpleNamespace(model="m")
    agent._external_pause_event = asyncio.Event()
    # ensure connection checks not used
    agent._is_connection_like_error = lambda e: False
    agent._is_browser_closed_error = lambda e: False

    async def demo_log(msg, level, meta):
        raise AssertionError("demo_log should not be called for InterruptedError")
    agent._demo_mode_log_override = demo_log

    # Call with InterruptedError that has a message
    err = InterruptedError("user cancelled")
    result = await agent._handle_step_error(err)

    # Assert return is None and warning logged with the message
    assert result is None
    assert agent.state.last_result is None
    assert ("warning", "The agent was interrupted mid-step - user cancelled") in agent.logger.calls


@pytest.mark.asyncio
async def test_handle_step_error_reconnect_success():
    agent = object.__new__(TestAgent)
    agent.logger = FakeLogger()
    agent.state = SimpleNamespace(consecutive_failures=0, last_result=None, stopped=False, n_steps=1)
    agent.settings = SimpleNamespace(max_failures=3, final_response_after_failure=False)
    agent.llm = SimpleNamespace(model="mymodel")
    agent._external_pause_event = asyncio.Event()

    # Simulate browser_session which is reconnecting and will become connected
    reconnect_event = asyncio.Event()
    reconnect_event.set()  # already set so wait_for will return immediately

    browser_session = SimpleNamespace(
        is_reconnecting=True,
        RECONNECT_WAIT_TIMEOUT=0.5,
        _reconnect_event=reconnect_event,
        is_cdp_connected=True,
    )
    agent.browser_session = browser_session

    # Mark this as a connection-like error and not a closed-browser error
    agent._is_connection_like_error = lambda e: True
    agent._is_browser_closed_error = lambda e: False

    # Capture demo log calls
    demo_calls = []

    async def demo_log(msg, level, meta):
        demo_calls.append((msg, level, meta))

    agent._demo_mode_log_override = demo_log

    # Use a generic exception
    err = Exception("lost conn")
    result = await agent._handle_step_error(err)

    # Because reconnection succeeded, function should set last_result to recovered message and return
    assert result is None
    assert isinstance(agent.state.last_result, list)
    assert len(agent.state.last_result) == 1
    assert isinstance(agent.state.last_result[0], ActionResult)
    assert "Connection lost and recovered: lost conn" in agent.state.last_result[0].error
    # Should have logged a warning and an info
    assert any(call[0] == "warning" for call in agent.logger.calls)
    assert any(call[0] == "info" for call in agent.logger.calls)
    # demo_log should NOT have been called in this path
    assert demo_calls == []


@pytest.mark.asyncio
async def test_handle_step_error_browser_closed_sets_stopped_and_external_pause():
    agent = object.__new__(TestAgent)
    agent.logger = FakeLogger()
    agent.state = SimpleNamespace(consecutive_failures=0, last_result=None, stopped=False, n_steps=2)
    agent.settings = SimpleNamespace(max_failures=2, final_response_after_failure=False)
    agent.llm = SimpleNamespace(model="mymodel")
    agent._external_pause_event = asyncio.Event()

    browser_session = SimpleNamespace(
        is_reconnecting=False,
    )
    agent.browser_session = browser_session

    agent._is_connection_like_error = lambda e: True
    agent._is_browser_closed_error = lambda e: True

    async def demo_log(msg, level, meta):
        raise AssertionError("demo_log should not be called for browser closed path")

    agent._demo_mode_log_override = demo_log

    err = RuntimeError("cdp closed")
    result = await agent._handle_step_error(err)

    # Should return None and set stopped True and set external pause event
    assert result is None
    assert agent.state.stopped is True
    # external event should be set
    assert agent._external_pause_event.is_set()
    # warning should contain the browser closed text (emoji may be present)
    assert any("Browser closed or disconnected" in call[1] for call in agent.logger.calls if call[0] == "warning")


@pytest.mark.asyncio
async def test_handle_step_error_parse_failure_and_final(monkeypatch):
    agent = object.__new__(TestAgent)
    # Enable debug False (default)
    agent.logger = FakeLogger(debug_enabled=False)
    # Set consecutive_failures to 0 so after increment it equals max_total_failures
    agent.state = SimpleNamespace(consecutive_failures=0, last_result=None, stopped=False, n_steps=3)
    # Make max_failures small to trigger final failure state
    agent.settings = SimpleNamespace(max_failures=1, final_response_after_failure=False)
    agent.llm = SimpleNamespace(model="mymodel")
    agent._external_pause_event = asyncio.Event()

    # Not a connection-like error
    agent._is_connection_like_error = lambda e: False
    agent._is_browser_closed_error = lambda e: False

    # Monkeypatch AgentError.format_error to return a parse-failure string
    monkeypatch.setattr(AgentError, "format_error", staticmethod(lambda e, include_trace=False: "Could not parse response: bad output"))

    demo_calls = []

    async def demo_log(msg, level, meta):
        demo_calls.append((msg, level, meta))

    agent._demo_mode_log_override = demo_log

    # Use a ValueError to pass into format_error
    err = ValueError("model output broken")
    result = await agent._handle_step_error(err)

    # After handling, last_result should be set to ActionResult with the formatted message
    assert result is None
    assert isinstance(agent.state.last_result, list) and isinstance(agent.state.last_result[0], ActionResult)
    assert "Could not parse response: bad output" in agent.state.last_result[0].error
    # Because message contained the parse hint, logger should have a "Model:" log and the prefix log
    has_model_log = any(call[0] == "log" and "Model: mymodel failed" in call[2] for call in agent.logger.calls)
    has_prefix_log = any(call[0] == "log" and "❌ Result failed 1/1 times:" in call[2] for call in agent.logger.calls)
    assert has_model_log, f"logger.calls: {agent.logger.calls}"
    assert has_prefix_log, f"logger.calls: {agent.logger.calls}"
    # demo_log must have been awaited once with error message
    assert len(demo_calls) == 1
    assert "Step error: Could not parse response: bad output" in demo_calls[0][0]
