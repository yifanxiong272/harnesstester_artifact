# file: pr_agent/algo/ai_handlers/litellm_helpers.py:9-42
# asked: {"lines": [19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42], "branches": [[23, 24], [23, 36], [24, 25], [24, 36], [28, 29], [28, 30], [30, 31], [30, 36], [36, 37], [36, 39], [39, 40], [39, 42]]}
# gained: {"lines": [19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42], "branches": [[23, 24], [23, 36], [24, 25], [28, 29], [28, 30], [30, 31], [30, 36], [36, 37], [36, 39], [39, 40], [39, 42]]}

import pytest
import types

from pr_agent.algo.ai_handlers import litellm_helpers as helpers


class CustomAPIError(Exception):
    pass


class RecordingLogger:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.debugs = []

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


@pytest.mark.asyncio
async def test_successful_streaming_response(monkeypatch):
    logger = RecordingLogger()
    # Patch get_logger to return our recording logger
    monkeypatch.setattr(helpers, "get_logger", lambda: logger)
    # Ensure APIError is our controlled exception type (not used in this test)
    monkeypatch.setattr(helpers.openai, "APIError", CustomAPIError, raising=False)

    # Create chunk objects
    Chunk = types.SimpleNamespace
    Choice = types.SimpleNamespace
    Delta = types.SimpleNamespace

    async def response_gen():
        yield Chunk(choices=[Choice(delta=Delta(content="Hello "), finish_reason=None)])
        yield Chunk(choices=[Choice(delta=Delta(content="world"), finish_reason="stop")])

    full, reason = await helpers._handle_streaming_response(response_gen())
    assert full == "Hello world"
    assert reason == "stop"
    # No errors or warnings should have been recorded
    assert logger.errors == []
    assert logger.warnings == []
    # debug may or may not be used; in this flow it shouldn't be used for the empty-content branches
    assert logger.debugs == []


@pytest.mark.asyncio
async def test_empty_response_no_finish_reason_raises(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(helpers, "get_logger", lambda: logger)
    monkeypatch.setattr(helpers.openai, "APIError", CustomAPIError, raising=False)

    async def empty_gen():
        if False:
            yield  # never yields

    with pytest.raises(CustomAPIError) as excinfo:
        await helpers._handle_streaming_response(empty_gen())
    assert "Empty streaming response received without proper completion" in str(excinfo.value)
    # ensure warning was logged
    assert any("Streaming response resulted in empty content with no finish reason" in w for w in logger.warnings)


@pytest.mark.asyncio
async def test_empty_response_with_finish_reason_raises(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(helpers, "get_logger", lambda: logger)
    monkeypatch.setattr(helpers.openai, "APIError", CustomAPIError, raising=False)

    Chunk = types.SimpleNamespace
    Choice = types.SimpleNamespace
    # delta without content attribute
    Delta = types.SimpleNamespace

    async def response_gen():
        yield Chunk(choices=[Choice(delta=Delta(), finish_reason="length")])

    with pytest.raises(CustomAPIError) as excinfo:
        await helpers._handle_streaming_response(response_gen())
    assert "Streaming response completed with finish_reason 'length' but no content received" in str(excinfo.value)
    # ensure debug was logged with the finish reason
    assert any("completed with finish_reason: length" in d or "finish_reason 'length'" in d for d in logger.debugs)


@pytest.mark.asyncio
async def test_exception_during_iteration_logs_and_reraises(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(helpers, "get_logger", lambda: logger)
    monkeypatch.setattr(helpers.openai, "APIError", CustomAPIError, raising=False)

    class BadAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError) as excinfo:
        await helpers._handle_streaming_response(BadAsyncIter())
    assert "boom" in str(excinfo.value)
    # ensure error was logged containing the exception text
    assert any("Error handling streaming response" in e and "boom" in e for e in logger.errors)
