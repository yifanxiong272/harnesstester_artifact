# file: gpt_researcher/agent.py:310-328
# asked: {"lines": [312, 313, 314, 315, 316, 317, 318, 319, 322, 323, 324, 326, 327, 328], "branches": [[312, 0], [312, 313], [314, 315], [314, 316], [316, 317], [316, 318], [318, 319], [318, 322]]}
# gained: {"lines": [312, 313, 314, 315, 316, 317, 318, 319, 322, 323, 324, 326, 327, 328], "branches": [[312, 313], [314, 315], [314, 316], [316, 317], [316, 318], [318, 319]]}

import pytest
import logging

from gpt_researcher.agent import GPTResearcher


@pytest.mark.asyncio
async def test_log_event_tool_calls_handler_and_logs_info_without_conflict(caplog):
    # Create instance without running __init__
    researcher = object.__new__(GPTResearcher)

    calls = []

    class Handler:
        async def on_tool_start(self, tool_name, **kwargs):
            calls.append(("tool", tool_name, dict(kwargs)))

    researcher.log_handler = Handler()

    caplog.set_level(logging.INFO, logger="research")

    # Pass a different key than 'tool_name' to avoid the duplicate-key bug in the implementation
    await researcher._log_event("tool", name="hammer", extra="value")

    # Handler should have been called; tool_name will be empty string because implementation looks up 'tool_name'
    assert ("tool", "", {"name": "hammer", "extra": "value"}) in calls

    # Logger should have an info record with the JSON payload including our provided keys
    found = any(
        record.levelno == logging.INFO and "tool" in record.getMessage() and '"name": "hammer"' in record.getMessage()
        for record in caplog.records
    )
    assert found, f"Expected INFO log with tool event and payload; logs: {[r.getMessage() for r in caplog.records]}"


@pytest.mark.asyncio
async def test_log_event_action_calls_handler_and_logs_info_without_conflict(caplog):
    researcher = object.__new__(GPTResearcher)

    calls = []

    class Handler:
        async def on_agent_action(self, action, **kwargs):
            calls.append(("action", action, dict(kwargs)))

    researcher.log_handler = Handler()

    caplog.set_level(logging.INFO, logger="research")

    # Avoid using the 'action' key to prevent duplicate-key error in implementation
    await researcher._log_event("action", act="do_something", param=123)

    # action positional arg will be empty string (implementation uses kwargs.get('action',''))
    assert ("action", "", {"act": "do_something", "param": 123}) in calls

    found = any(
        record.levelno == logging.INFO and "action" in record.getMessage() and '"param": 123' in record.getMessage()
        for record in caplog.records
    )
    assert found, f"Expected INFO log with action event; logs: {[r.getMessage() for r in caplog.records]}"


@pytest.mark.asyncio
async def test_log_event_research_calls_handler_and_logs_info(caplog):
    researcher = object.__new__(GPTResearcher)

    calls = []

    class Handler:
        async def on_research_step(self, step, details):
            calls.append(("research", step, details))

    researcher.log_handler = Handler()

    caplog.set_level(logging.INFO, logger="research")

    details = {"foo": "bar", "num": 7}
    # For 'research', implementation passes step and details directly (no kwargs expansion), so use these keys
    await researcher._log_event("research", step="step1", details=details)

    assert ("research", "step1", details) in calls

    found = any(
        record.levelno == logging.INFO and "research" in record.getMessage() and '"foo": "bar"' in record.getMessage()
        for record in caplog.records
    )
    assert found, f"Expected INFO log with research event; logs: {[r.getMessage() for r in caplog.records]}"


@pytest.mark.asyncio
async def test_log_event_handler_exception_logs_error(caplog):
    researcher = object.__new__(GPTResearcher)

    class Handler:
        async def on_tool_start(self, tool_name, **kwargs):
            raise RuntimeError("boom")

    researcher.log_handler = Handler()

    caplog.set_level(logging.ERROR, logger="research")

    # Avoid duplicate-key TypeError by not passing 'tool_name'; the handler itself will raise
    await researcher._log_event("tool", name="drill")

    found_error = any(
        record.levelno >= logging.ERROR and "Error in _log_event" in record.getMessage() and "boom" in record.getMessage()
        for record in caplog.records
    )
    assert found_error, f"Expected ERROR log about handler exception; logs: {[r.getMessage() for r in caplog.records]}"
