import asyncio
import logging
import types
import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import ActionResult, AgentError


class DummyLogger:
    def __init__(self, debug_enabled=False):
        self.warnings = []
        self.infos = []
        self.logs = []
        self._debug_enabled = debug_enabled

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def log(self, level, msg):
        self.logs.append((level, msg))

    def isEnabledFor(self, level):
        # emulate only debug flag behavior used in code under test
        if level == logging.DEBUG:
            return self._debug_enabled
        return True


class DummyEvent:
    def __init__(self, coro):
        # coro should be an async callable returning or raising
        self._coro = coro

    async def wait(self):
        return await self._coro()


class DummyBrowserSession:
    def __init__(self, is_reconnecting=False, is_cdp_connected=False, wait_coro=None, timeout=0.01):
        self.is_reconnecting = is_reconnecting
        self.is_cdp_connected = is_cdp_connected
        self.RECONNECT_WAIT_TIMEOUT = timeout
        # default event that returns immediately unless provided
        if wait_coro is None:
            async def immediate():
                return True

            wait_coro = immediate
        self._reconnect_event = DummyEvent(wait_coro)


class DummyExternalPauseEvent:
    def __init__(self):
        self.was_set = False

    def set(self):
        self.was_set = True


class DummyState:
    def __init__(self):
        self.last_result = None
        self.stopped = False
        self.consecutive_failures = 0
        self.n_steps = 3


class DummySettings:
    def __init__(self, max_failures=1, final_response_after_failure=False):
        self.max_failures = max_failures
        self.final_response_after_failure = final_response_after_failure


class DummyLLM:
    def __init__(self, model_name="test-model"):
        self.model = model_name


class DummySelf:
    """A minimal object shaped like Agent for testing _handle_step_error."""

    def __init__(self):
        self.logger = DummyLogger()
        self.browser_session = DummyBrowserSession()
        self._external_pause_event = DummyExternalPauseEvent()
        self.state = DummyState()
        self.settings = DummySettings()
        self.llm = DummyLLM()
        # capture demo logs
        self.demo_logs = []

    async def _demo_mode_log(self, message, level, metadata):
        # record the values for assertions
        self.demo_logs.append((message, level, metadata))

    # hooks used in the function under test; default to False
    def _is_connection_like_error(self, error):
        return False

    def _is_browser_closed_error(self, error):
        return False


@pytest.mark.asyncio
async def test_handle_step_error_interrupted_round_067():
    dummy = DummySelf()
    # make logger debug state irrelevant
    err = InterruptedError("user-stop")

    # Call the method. Using unbound function to pass our dummy in place of self.
    result = await Agent._handle_step_error(dummy, err)

    # Should have logged a warning and returned early (None)
    assert dummy.logger.warnings, "warning not logged for InterruptedError"
    assert any("The agent was interrupted mid-step" in w for w in dummy.logger.warnings)
    assert result is None


@pytest.mark.asyncio
async def test_handle_step_error_reconnect_succeeds_round_067():
    dummy = DummySelf()

    # Simulate a reconnection in progress that completes and results in CDP connected
    async def immediate_wait():
        return True

    dummy.browser_session = DummyBrowserSession(
        is_reconnecting=True, is_cdp_connected=True, wait_coro=immediate_wait, timeout=0.05
    )

    # mark connection-like to enter the reconnection logic
    dummy._is_connection_like_error = lambda e: True

    err = Exception("connection dropped")
    result = await Agent._handle_step_error(dummy, err)

    # Should have info logged about reconnection succeeded
    assert any("Reconnection succeeded" in i for i in dummy.logger.infos), "reconnection success info not logged"

    # state.last_result should be set to an ActionResult instance containing the original error text
    assert isinstance(dummy.state.last_result, list)
    assert isinstance(dummy.state.last_result[0], ActionResult)
    assert "Connection lost and recovered" in dummy.state.last_result[0].error
    # method returns early -> None
    assert result is None


@pytest.mark.asyncio
async def test_handle_step_error_browser_closed_after_timeout_round_067(monkeypatch):
    dummy = DummySelf()

    # Simulate reconnection in progress but wait_for timing out
    async def never_complete():
        # do not return to simulate pending wait
        await asyncio.sleep(0)
        # but immediately raise TimeoutError when awaited by the patched wait_for
        return True

    dummy.browser_session = DummyBrowserSession(
        is_reconnecting=True, is_cdp_connected=False, wait_coro=never_complete, timeout=0.01
    )

    # mark connection-like to enter reconnection logic
    dummy._is_connection_like_error = lambda e: True
    # mark browser as closed so after timeout the browser-closed branch triggers
    dummy._is_browser_closed_error = lambda e: True

    # Patch asyncio.wait_for inside the module to raise TimeoutError deterministically
    async def fake_wait_for(awaitable, timeout):
        raise TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    err = Exception("disconnected")
    result = await Agent._handle_step_error(dummy, err)

    # Should have logged a browser-closed warning
    assert any("Browser closed or disconnected" in w for w in dummy.logger.warnings)

    # Should have set stopped flag and external pause event
    assert dummy.state.stopped is True
    assert dummy._external_pause_event.was_set is True
    assert result is None


@pytest.mark.asyncio
async def test_handle_step_error_parse_error_logs_model_hint_round_067(monkeypatch):
    dummy = DummySelf()
    # Not a connection-like error
    dummy._is_connection_like_error = lambda e: False

    # Make AgentError.format_error return a message that contains the parse-failure substring
    formatted = "Could not parse response: bad json"
    monkeypatch.setattr(AgentError, "format_error", staticmethod(lambda error, include_trace: formatted))

    # Ensure that logger debug is enabled so include_trace True path is exercised
    dummy.logger._debug_enabled = True

    # Choose settings so that this becomes a final failure (max_failures=1, final_response_after_failure False)
    dummy.settings = DummySettings(max_failures=1, final_response_after_failure=False)
    dummy.state.consecutive_failures = 0

    dummy.llm = DummyLLM(model_name="X-Model")

    err = Exception("parse fail")
    await Agent._handle_step_error(dummy, err)

    # When parse-related error, first log should be a hint to model
    levels_and_msgs = dummy.logger.logs
    assert levels_and_msgs, "no logger.log calls found"
    # First log entry should mention Model: <model>
    assert any("Model: X-Model failed" in msg for lvl, msg in levels_and_msgs), "model hint log missing"
    # final error log should include the prefix about failure counts
    assert any("Result failed" in msg for lvl, msg in levels_and_msgs), "failure-count prefix log missing"

    # demo log called with Step error message and metadata containing step number
    assert dummy.demo_logs and dummy.demo_logs[0][1] == "error"
    assert dummy.demo_logs[0][2]["step"] == dummy.state.n_steps

    # last_result set to ActionResult with the formatted message
    assert isinstance(dummy.state.last_result, list)
    assert isinstance(dummy.state.last_result[0], ActionResult)
    assert formatted == dummy.state.last_result[0].error


@pytest.mark.asyncio
async def test_handle_step_error_other_exception_warning_round_067(monkeypatch):
    dummy = DummySelf()
    dummy._is_connection_like_error = lambda e: False

    # Make AgentError.format_error return a message that does NOT contain parse/tool substrings
    formatted = "Some other error occurred"
    monkeypatch.setattr(AgentError, "format_error", staticmethod(lambda error, include_trace: formatted))

    # settings such that this is a partial failure (max_failures big)
    dummy.settings = DummySettings(max_failures=5, final_response_after_failure=False)
    dummy.state.consecutive_failures = 0

    # ensure debug disabled so include_trace False path is exercised
    dummy.logger._debug_enabled = False

    err = Exception("other")
    await Agent._handle_step_error(dummy, err)

    # Should have logged exactly one failure message (no model hint)
    assert not any("Model:" in msg for lvl, msg in dummy.logger.logs), "model hint should not be logged"
    assert any("Result failed" in msg for lvl, msg in dummy.logger.logs), "failure prefix log missing"

    # Since not final, should log WARNING level
    assert any(lvl == logging.WARNING for lvl, msg in dummy.logger.logs)

    # demo log and last_result set
    assert dummy.demo_logs and dummy.demo_logs[0][1] == "error"
    assert isinstance(dummy.state.last_result[0], ActionResult)
    assert formatted == dummy.state.last_result[0].error
