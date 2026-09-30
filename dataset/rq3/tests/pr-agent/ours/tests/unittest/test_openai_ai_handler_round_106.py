import pytest
import types
import builtins

from pr_agent.algo.ai_handlers import openai_ai_handler as handler_mod
import openai
from pr_agent.algo.ai_handlers.openai_ai_handler import OpenAIHandler


class DummyLogger:
    def __init__(self):
        self.records = []

    def info(self, *args, **kwargs):
        self.records.append(("info", args, kwargs))

    def warning(self, *args, **kwargs):
        self.records.append(("warning", args, kwargs))

    def error(self, *args, **kwargs):
        self.records.append(("error", args, kwargs))


class MockCompletions:
    def __init__(self, to_return=None, to_raise=None):
        self._to_return = to_return
        self._to_raise = to_raise
        self.last_call = None

    async def create(self, *args, **kwargs):
        # record call for assertions
        self.last_call = {"args": args, "kwargs": kwargs}
        if self._to_raise is not None:
            raise self._to_raise
        return self._to_return


class MockChat:
    def __init__(self, completions):
        self.completions = completions


class MockAsyncOpenAI:
    def __init__(self, completions):
        # client.chat.completions.create
        self.chat = MockChat(completions)


@pytest.mark.asyncio
async def test_chat_completion_no_image_round_106(monkeypatch):
    """Normal path: img_path is falsy. Verify create called with expected args and return values."""
    # Prepare a deterministic response object matching expected shape
    class Msg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, msg, finish_reason):
            self.message = msg
            self.finish_reason = finish_reason

    mock_response = types.SimpleNamespace(
        choices=[Choice(Msg("hello"), "stop")],
        usage={"tokens": 5},
    )

    completions = MockCompletions(to_return=mock_response)
    mock_client = MockAsyncOpenAI(completions)

    # Patch the AsyncOpenAI used inside the module under test
    monkeypatch.setattr(handler_mod, "AsyncOpenAI", lambda: mock_client)

    # Patch logger to capture logs
    dummy_logger = DummyLogger()
    monkeypatch.setattr(handler_mod, "get_logger", lambda: dummy_logger)

    # Create instance without running __init__ to avoid unrelated side effects
    inst = object.__new__(OpenAIHandler)

    resp, finish_reason = await inst.chat_completion(model="gpt-test", system="SYS", user="USR", temperature=0.1, img_path=None)

    # Assertions on returned values
    assert resp == "hello"
    assert finish_reason == "stop"

    # Assert that the mock create got called with the expected parameters
    called = completions.last_call
    assert called is not None
    assert called["kwargs"]["model"] == "gpt-test"
    # messages should include the system and user messages in order
    assert called["kwargs"]["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USR"}]
    assert called["kwargs"]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_chat_completion_with_image_round_106(monkeypatch):
    """img_path truthy: branch that logs a warning but continues to call API."""
    # Reuse response shape
    class Msg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, msg, finish_reason):
            self.message = msg
            self.finish_reason = finish_reason

    mock_response = types.SimpleNamespace(
        choices=[Choice(Msg("img-ignored"), "length")],
        usage={"tokens": 3},
    )

    completions = MockCompletions(to_return=mock_response)
    mock_client = MockAsyncOpenAI(completions)

    monkeypatch.setattr(handler_mod, "AsyncOpenAI", lambda: mock_client)

    dummy_logger = DummyLogger()
    monkeypatch.setattr(handler_mod, "get_logger", lambda: dummy_logger)

    inst = object.__new__(OpenAIHandler)

    resp, finish_reason = await inst.chat_completion(model="gpt-test", system="S", user="U", temperature=0.2, img_path="/tmp/fake.png")

    assert resp == "img-ignored"
    assert finish_reason == "length"

    # Confirm a warning record was emitted about ignoring image path
    warnings = [r for r in dummy_logger.records if r[0] == "warning"]
    assert any("Image path is not supported" in str(a) or "/tmp/fake.png" in str(a) for _, a, _ in warnings)

    # And the API call still happened with expected messages
    called = completions.last_call
    assert called is not None
    assert called["kwargs"]["messages"][0]["content"] == "S"
    assert called["kwargs"]["messages"][1]["content"] == "U"


@pytest.mark.asyncio
async def test_rate_limit_error_round_106(monkeypatch):
    """When the underlying client raises openai.RateLimitError, it should be re-raised."""
    completions = MockCompletions(to_raise=openai.RateLimitError("rate limited"))
    mock_client = MockAsyncOpenAI(completions)

    monkeypatch.setattr(handler_mod, "AsyncOpenAI", lambda: mock_client)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(handler_mod, "get_logger", lambda: dummy_logger)

    inst = object.__new__(OpenAIHandler)

    with pytest.raises(openai.RateLimitError):
        await inst.chat_completion(model="m", system="s", user="u")

    # Ensure an error log was recorded
    errors = [r for r in dummy_logger.records if r[0] == "error"]
    assert errors, "Expected an error log entry for RateLimitError"


@pytest.mark.asyncio
async def test_api_error_round_106(monkeypatch):
    """When the underlying client raises openai.APIError, it should be re-raised unchanged."""
    completions = MockCompletions(to_raise=openai.APIError("api failure"))
    mock_client = MockAsyncOpenAI(completions)

    monkeypatch.setattr(handler_mod, "AsyncOpenAI", lambda: mock_client)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(handler_mod, "get_logger", lambda: dummy_logger)

    inst = object.__new__(OpenAIHandler)

    with pytest.raises(openai.APIError):
        await inst.chat_completion(model="m", system="s", user="u")

    # Ensure a warning log was recorded for APIError branch
    warnings = [r for r in dummy_logger.records if r[0] == "warning"]
    assert warnings, "Expected a warning log entry for APIError"


@pytest.mark.asyncio
async def test_unknown_exception_wrapped_as_api_error_round_106(monkeypatch):
    """If a generic exception occurs, the code wraps it into openai.APIError."""
    # Underlying create raises a generic ValueError
    completions = MockCompletions(to_raise=ValueError("boom"))
    mock_client = MockAsyncOpenAI(completions)

    monkeypatch.setattr(handler_mod, "AsyncOpenAI", lambda: mock_client)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(handler_mod, "get_logger", lambda: dummy_logger)

    inst = object.__new__(OpenAIHandler)

    with pytest.raises(openai.APIError) as excinfo:
        await inst.chat_completion(model="m", system="s", user="u")

    # The raised APIError should have the original exception as its __cause__
    assert isinstance(excinfo.value.__cause__, ValueError)
    # Confirm a warning was logged about unknown error
    warnings = [r for r in dummy_logger.records if r[0] == "warning"]
    assert warnings, "Expected a warning log entry for unknown exception"
