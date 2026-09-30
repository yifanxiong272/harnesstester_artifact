# file: pr_agent/algo/ai_handlers/litellm_helpers.py:9-42
# asked: {"lines": [19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42], "branches": [[23, 24], [23, 36], [24, 25], [24, 36], [28, 29], [28, 30], [30, 31], [30, 36], [36, 37], [36, 39], [39, 40], [39, 42]]}
# gained: {"lines": [19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42], "branches": [[23, 24], [23, 36], [24, 25], [28, 29], [28, 30], [30, 31], [30, 36], [36, 37], [36, 39], [39, 40], [39, 42]]}

import pytest
from types import SimpleNamespace

import pr_agent.algo.ai_handlers.litellm_helpers as lmh


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


class CustomAPIError(Exception):
    pass


def make_chunk(content=None, finish_reason=None):
    # Build the nested structure: chunk.choices[0].delta.content and .finish_reason
    delta = SimpleNamespace(content=content)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    chunk = SimpleNamespace(choices=[choice])
    return chunk


@pytest.mark.asyncio
async def test_handle_streaming_response_success(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(lmh, "get_logger", lambda: dummy)

    # Ensure APIError remains available (not used here)
    monkeypatch.setattr(lmh.openai, "APIError", CustomAPIError, raising=False)

    async def gen():
        # first yields content, no finish_reason
        yield make_chunk(content="hello", finish_reason=None)
        # then yields no content but finish_reason
        yield make_chunk(content=None, finish_reason="stop")

    result = await lmh._handle_streaming_response(gen())
    assert result == ("hello", "stop")
    # no warnings or errors expected
    assert dummy.errors == []
    assert dummy.warnings == []
    assert dummy.debugs == []


@pytest.mark.asyncio
async def test_handle_streaming_response_empty_no_finish(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(lmh, "get_logger", lambda: dummy)
    # Replace APIError so we can catch it specifically
    monkeypatch.setattr(lmh.openai, "APIError", CustomAPIError, raising=False)

    async def gen():
        # yield a chunk with no content and no finish_reason
        yield make_chunk(content=None, finish_reason=None)

    with pytest.raises(CustomAPIError) as excinfo:
        await lmh._handle_streaming_response(gen())

    assert "Empty streaming response received without proper completion" in str(excinfo.value)
    # warning should have been called
    assert any("Streaming response resulted in empty content with no finish reason" in w for w in dummy.warnings)
    # no debug or error expected
    assert dummy.errors == []
    assert dummy.debugs == []


@pytest.mark.asyncio
async def test_handle_streaming_response_empty_with_finish(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(lmh, "get_logger", lambda: dummy)
    monkeypatch.setattr(lmh.openai, "APIError", CustomAPIError, raising=False)

    async def gen():
        # yield a chunk with no content but with a finish_reason
        yield make_chunk(content=None, finish_reason="stop")

    with pytest.raises(CustomAPIError) as excinfo:
        await lmh._handle_streaming_response(gen())

    assert "Streaming response completed with finish_reason 'stop' but no content received" in str(excinfo.value)
    # debug should have been called with the finish reason
    assert any("completed with finish_reason: stop" in d or "finish_reason 'stop'" in d for d in dummy.debugs)


@pytest.mark.asyncio
async def test_handle_streaming_response_iteration_exception(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(lmh, "get_logger", lambda: dummy)

    # Create an async iterable whose __anext__ raises
    class BadAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("boom during iteration")

    with pytest.raises(RuntimeError) as excinfo:
        await lmh._handle_streaming_response(BadAsyncIter())

    assert "boom during iteration" in str(excinfo.value)
    # Ensure the logger.error was called and contains the exception message
    assert any("Error handling streaming response" in e and "boom during iteration" in e for e in dummy.errors)
