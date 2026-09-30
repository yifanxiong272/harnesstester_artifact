import pytest
import types
import openai

from pr_agent.algo.ai_handlers import litellm_helpers
from pr_agent.algo.ai_handlers.litellm_helpers import _handle_streaming_response


class DummyLogger:
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


class Chunk:
    def __init__(self, choices):
        self.choices = choices


class Delta:
    def __init__(self, content=None):
        self.content = content


class Choice:
    def __init__(self, delta=None, finish_reason=None):
        self.delta = delta or Delta()
        self.finish_reason = finish_reason


async def _async_gen_from_list(items):
    for it in items:
        yield it


class BadAsyncIter:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise ValueError("iteration-failure")


@pytest.mark.asyncio
async def test_successful_stream_concat_round_065(monkeypatch):
    """
    Ensure chunks with content are concatenated and finish_reason is captured when present.
    """
    logger = DummyLogger()
    monkeypatch.setattr(litellm_helpers, "get_logger", lambda: logger)

    # Ensure openai.APIError is something testable (won't be used here but keep deterministic)
    class APITestErr(Exception):
        pass

    monkeypatch.setattr(openai, "APIError", APITestErr)

    # Create stream: two chunks with content, then a chunk with no content but a finish_reason
    chunks = [
        Chunk([Choice(delta=Delta(content="Hello "))]),
        Chunk([Choice(delta=Delta(content="world"))]),
        Chunk([Choice(delta=Delta(content=None), finish_reason="stop")]),
    ]

    result = await _handle_streaming_response(_async_gen_from_list(chunks))

    assert result == ("Hello world", "stop")
    # No warnings or errors should have been logged
    assert logger.errors == []
    assert logger.warnings == []
    # debug may or may not be invoked depending on path; in this path we expect no debug about empty content
    assert isinstance(result[0], str) and result[0].startswith("Hello")


@pytest.mark.asyncio
async def test_empty_no_finish_raises_round_065(monkeypatch):
    """
    If the stream yields no usable choices/content and no finish_reason, an openai.APIError is raised and a warning logged.
    """
    logger = DummyLogger()
    monkeypatch.setattr(litellm_helpers, "get_logger", lambda: logger)

    class APITestErr(Exception):
        pass

    monkeypatch.setattr(openai, "APIError", APITestErr)

    # Chunk with empty choices should cause no content and no finish_reason
    chunks = [
        Chunk([]),
    ]

    with pytest.raises(APITestErr):
        await _handle_streaming_response(_async_gen_from_list(chunks))

    # Ensure a warning was logged about empty content with no finish reason
    assert any("empty content" in w.lower() or "empty streaming response" in w.lower() for w in logger.warnings)


@pytest.mark.asyncio
async def test_empty_with_finish_raises_round_065(monkeypatch):
    """
    If the stream yields a finish_reason but no content, an APIError mentioning the finish_reason should be raised and debug logged.
    """
    logger = DummyLogger()
    monkeypatch.setattr(litellm_helpers, "get_logger", lambda: logger)

    class APITestErr(Exception):
        pass

    monkeypatch.setattr(openai, "APIError", APITestErr)

    # Chunk with a choice that has no content but has a finish_reason
    chunks = [
        Chunk([Choice(delta=Delta(content=None), finish_reason="timeout")]),
    ]

    with pytest.raises(APITestErr) as excinfo:
        await _handle_streaming_response(_async_gen_from_list(chunks))

    # The raised APIError message should include the finish_reason string
    assert "timeout" in str(excinfo.value)
    # And a debug log should exist mentioning the finish_reason
    assert any("finish_reason" in d.lower() or "timeout" in d.lower() for d in logger.debugs)


@pytest.mark.asyncio
async def test_exception_during_iteration_round_065(monkeypatch):
    """
    If iteration raises an exception, it should be logged as an error and re-raised.
    """
    logger = DummyLogger()
    monkeypatch.setattr(litellm_helpers, "get_logger", lambda: logger)

    # Ensure openai.APIError is present but not involved here
    class APITestErr(Exception):
        pass

    monkeypatch.setattr(openai, "APIError", APITestErr)

    with pytest.raises(ValueError) as excinfo:
        await _handle_streaming_response(BadAsyncIter())

    assert "iteration-failure" in str(excinfo.value)
    # Ensure an error was logged containing our exception message
    assert any("Error handling streaming response" in e or "iteration-failure" in e for e in logger.errors)
