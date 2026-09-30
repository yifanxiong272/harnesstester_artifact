import asyncio
from typing import Any, Dict

import gpt_researcher.actions.utils as utils


class FakeLogger:
    def __init__(self):
        self.error_calls = []  # list of (msg, kwargs)
        self.warning_calls = []  # list of (msg, kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        # record message and kwargs (e.g., exc_info)
        self.error_calls.append((msg, kwargs))

    def warning(self, msg: str, **kwargs: Any) -> None:
        self.warning_calls.append((msg, kwargs))


class FakeWebSocketSuccess:
    def __init__(self):
        self.sent = None

    async def send_json(self, data: Dict[str, Any]) -> None:
        # emulate successful send
        self.sent = data


class FakeWebSocketRaise:
    def __init__(self, exc_message: str):
        self.exc_message = exc_message

    async def send_json(self, data: Dict[str, Any]) -> None:
        # Always raise the provided exception message
        raise Exception(self.exc_message)


def test_safe_send_json_success_round_101():
    """Verify successful send calls websocket.send_json with the given data."""
    ws = FakeWebSocketSuccess()
    data = {"hello": "world"}

    # Run the async function synchronously
    asyncio.run(utils.safe_send_json(ws, data))

    assert ws.sent == data, "WebSocket should have received the same data on success"


def test_safe_send_json_closed_connection_round_101():
    """
    If send_json raises an exception whose message contains 'closed' or 'connection',
    safe_send_json should call logger.error and then logger.warning with the
    closed-connection message.
    """
    fake_logger = FakeLogger()
    orig_logger = getattr(utils, "logger", None)
    utils.logger = fake_logger

    try:
        ws = FakeWebSocketRaise("Connection was CLOSED by client")
        asyncio.run(utils.safe_send_json(ws, {"k": "v"}))

        # logger.error should have been called once with the formatted message
        assert len(fake_logger.error_calls) == 1, "logger.error must be called once on exception"
        err_msg, err_kwargs = fake_logger.error_calls[0]
        # The formatted message must include the prefix and the exception details
        assert "Error sending JSON through WebSocket:" in err_msg
        assert "Exception:" in err_msg or "Exception" in err_msg
        assert "Connection was CLOSED by client" in err_msg
        # exc_info should be True according to implementation
        assert err_kwargs.get("exc_info") is True

        # logger.warning should have been called with the closed-connection hint
        assert len(fake_logger.warning_calls) == 1, "logger.warning must be called for closed/connection errors"
        warn_msg, _ = fake_logger.warning_calls[0]
        assert "WebSocket connection appears to be closed. Client may have disconnected." == warn_msg
    finally:
        # restore original logger to avoid cross-test contamination
        if orig_logger is not None:
            utils.logger = orig_logger


def test_safe_send_json_timeout_round_101():
    """
    If send_json raises an exception whose message contains 'timeout',
    safe_send_json should call logger.error and then logger.warning with the
    timeout-specific message.
    """
    fake_logger = FakeLogger()
    orig_logger = getattr(utils, "logger", None)
    utils.logger = fake_logger

    try:
        ws = FakeWebSocketRaise("timeout occurred while sending")
        asyncio.run(utils.safe_send_json(ws, {"x": 1}))

        # logger.error should have been called once
        assert len(fake_logger.error_calls) == 1, "logger.error must be called once on timeout"
        err_msg, err_kwargs = fake_logger.error_calls[0]
        assert "Error sending JSON through WebSocket:" in err_msg
        assert "timeout occurred while sending" in err_msg
        assert err_kwargs.get("exc_info") is True

        # logger.warning should have been called with timeout hint
        assert len(fake_logger.warning_calls) == 1, "logger.warning must be called for timeout errors"
        warn_msg, _ = fake_logger.warning_calls[0]
        assert "WebSocket send operation timed out. The client may be unresponsive." == warn_msg
    finally:
        if orig_logger is not None:
            utils.logger = orig_logger
