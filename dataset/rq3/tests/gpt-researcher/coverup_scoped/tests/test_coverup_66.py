# file: gpt_researcher/actions/utils.py:35-59
# asked: {"lines": [46, 47, 48, 49, 50, 51, 52, 53, 56, 57, 58, 59], "branches": [[56, 57], [56, 58], [58, 0], [58, 59]]}
# gained: {"lines": [46, 47, 48, 49, 50, 51, 52, 53, 56, 57, 58, 59], "branches": [[56, 57], [56, 58], [58, 59]]}

import logging
import pytest

from gpt_researcher.actions.utils import safe_send_json


class _FakeWebSocket:
    def __init__(self, exc_message: str):
        self._exc_message = exc_message

    async def send_json(self, data):
        raise Exception(self._exc_message)


@pytest.mark.asyncio
async def test_safe_send_json_logs_connection_closed_and_error(caplog):
    # Simulate an exception message that includes "connection" to hit the first warning branch
    ws = _FakeWebSocket("Connection was reset by peer")

    caplog.set_level(logging.WARNING)
    await safe_send_json(ws, {"test": "data"})

    # Ensure an error was logged
    assert any("Error sending JSON through WebSocket" in rec.getMessage() for rec in caplog.records)

    # Ensure the specific warning for closed/connection was logged
    assert any(
        "WebSocket connection appears to be closed. Client may have disconnected." in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_safe_send_json_logs_timeout_and_error(caplog):
    # Use a message that contains the exact substring "timeout" to hit the timeout warning branch
    ws = _FakeWebSocket("Send operation timeout occurred while writing")

    caplog.set_level(logging.WARNING)
    await safe_send_json(ws, {"another": "payload"})

    # Ensure an error was logged
    assert any("Error sending JSON through WebSocket" in rec.getMessage() for rec in caplog.records)

    # Ensure the specific timeout warning was logged
    assert any(
        "WebSocket send operation timed out. The client may be unresponsive." in rec.getMessage()
        for rec in caplog.records
    )
