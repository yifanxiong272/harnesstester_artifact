import asyncio
import pytest

from gpt_researcher.actions import utils


class FakeLogger:
    def __init__(self, raise_on_info=False):
        self.info_calls = []
        self.error_calls = []
        self.raise_on_info = raise_on_info

    def info(self, msg):
        if self.raise_on_info:
            # Simulate a logger raising a UnicodeEncodeError during info
            raise UnicodeEncodeError("utf-8", b"", 0, 1, "simulated")
        self.info_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


class FakeWebsocketSuccess:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        # Capture the payload for assertion
        self.sent.append(data)


class FakeWebsocketError:
    async def send_json(self, data):
        # Simulate an error when sending
        raise RuntimeError("send failed")


def test_logging_info_and_no_websocket_round_124(monkeypatch):
    """When websocket is None and type != 'images', logger.info should be called with the output."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "logger", fake_logger)

    # Run the async function synchronously for pytest
    asyncio.run(utils.stream_output("text", "content", "out", websocket=None, output_log=True, metadata=None))

    assert fake_logger.info_calls == ["out"]
    assert fake_logger.error_calls == []


def test_logging_unicode_error_calls_error_round_124(monkeypatch):
    """If logger.info raises UnicodeEncodeError, stream_output should call logger.error with a cp1252-replaced string."""
    # Use an output containing a character not representable in cp1252 (emoji)
    output_value = "bad😊"
    fake_logger = FakeLogger(raise_on_info=True)
    monkeypatch.setattr(utils, "logger", fake_logger)

    asyncio.run(utils.stream_output("text", "content", output_value, websocket=None, output_log=True, metadata=None))

    # Expect the emoji to be replaced when encoding with cp1252 and errors='replace'
    expected_transformed = output_value.encode("cp1252", errors="replace").decode("cp1252")
    assert fake_logger.info_calls == []
    assert fake_logger.error_calls == [expected_transformed]


def test_websocket_send_json_success_round_124(monkeypatch):
    """When a websocket is provided, stream_output should await websocket.send_json with the expected payload."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "logger", fake_logger)

    ws = FakeWebsocketSuccess()

    payload_type = "text"
    payload_content = "the-content"
    payload_output = "the-output"
    payload_metadata = {"k": "v"}

    asyncio.run(
        utils.stream_output(
            payload_type,
            payload_content,
            payload_output,
            websocket=ws,
            output_log=False,
            metadata=payload_metadata,
        )
    )

    assert fake_logger.info_calls == []  # logging skipped because output_log=False and websocket provided

    assert len(ws.sent) == 1
    assert ws.sent[0] == {
        "type": payload_type,
        "content": payload_content,
        "output": payload_output,
        "metadata": payload_metadata,
    }


def test_websocket_send_json_raises_round_124(monkeypatch):
    """If websocket.send_json raises, the exception should propagate out of stream_output."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "logger", fake_logger)

    ws = FakeWebsocketError()

    with pytest.raises(RuntimeError, match="send failed"):
        asyncio.run(
            utils.stream_output("text", "c", "o", websocket=ws, output_log=False, metadata=None)
        )

    # Ensure logging was not called in this path (output_log=False)
    assert fake_logger.info_calls == []
    assert fake_logger.error_calls == []
