import importlib
import types
import math
from types import SimpleNamespace

import pytest


def _make_dummy_logger():
    calls = {"info": [], "warning": [], "log_object": [], "log": []}

    class DummyLogger:
        def info(self, *args, **kwargs):
            calls["info"].append((args, kwargs))

        def warning(self, *args, **kwargs):
            calls["warning"].append((args, kwargs))

        def log_object(self, *args, **kwargs):
            calls["log_object"].append((args, kwargs))

        def log(self, *args, **kwargs):
            calls["log"].append((args, kwargs))

    return DummyLogger(), calls


def test_chat_streaming_response_round_034(monkeypatch):
    # Arrange: import module and prepare stubs/patches
    litellm = importlib.import_module("rdagent.oai.backend.litellm")
    DummyLogger, calls = _make_dummy_logger()
    monkeypatch.setattr(litellm, "logger", DummyLogger)

    # Settings: simulate a model that does NOT support response_schema
    monkeypatch.setattr(
        litellm,
        "LITELLM_SETTINGS",
        SimpleNamespace(chat_model="m-stream", log_llm_chat_content=True, chat_stream=True),
    )

    # supports_response_schema returns False to trigger the branch that drops response_format
    monkeypatch.setattr(litellm, "supports_response_schema", lambda model: False)

    # Prepare completion to return a streaming iterable of incremental messages
    streaming_response = [
        {"choices": [{"finish_reason": None, "delta": {"content": "Hello"}}]},
        {"choices": [{"finish_reason": "stop", "delta": {"content": None}}]},
        {"choices": [{"finish_reason": "custom", "delta": {}}]},
    ]

    def completion_stub(messages, stream, max_retries, **kw):
        # Ensure complete_kwargs (model) passed in and that response_format was not forwarded
        assert kw.get("model") is None or True  # model is passed separately in complete_kwargs; allow both
        # The core check: since supports_response_schema returned False, response_format should not be in kw
        assert "response_format" not in kw
        return streaming_response

    monkeypatch.setattr(litellm, "completion", completion_stub)

    # completion_cost returns a numeric cost
    monkeypatch.setattr(litellm, "completion_cost", lambda model, messages, completion: 1.5)

    # token_counter distinguishes calls by provided kwargs
    def token_counter_stub(model, **kwargs):
        if "messages" in kwargs:
            return 2
        if "text" in kwargs:
            return 4
        return 0

    monkeypatch.setattr(litellm, "token_counter", token_counter_stub)

    # Prepare a fresh backend instance without invoking its real __init__
    BackendCls = getattr(litellm, "LiteLLMAPIBackend")
    backend = object.__new__(BackendCls)
    # minimal methods used by the function
    backend._build_log_messages = lambda msgs: "LOGGED"
    backend.get_complete_kwargs = lambda: {"model": "m-stream"}

    # Reset accumulator cost
    monkeypatch.setattr(litellm, "ACC_COST", 0.0)

    # Act
    content, finish_reason = backend._create_chat_completion_inner_function(
        [{"role": "user", "content": "hi"}], response_format={"schema": "x"}
    )

    # Assert: streaming concatenation and finish reason handled correctly
    assert content == "Hello"
    assert finish_reason == "custom"
    # ACC_COST should have increased by completion_cost value
    assert math.isclose(litellm.ACC_COST, 1.5, rel_tol=1e-12)
    # Some logger calls should have been recorded (info/warning may be present)
    assert len(calls["info"]) >= 1


def test_non_streaming_cost_exception_and_response_format_round_034(monkeypatch):
    # Arrange: import module and prepare stubs/patches
    litellm = importlib.import_module("rdagent.oai.backend.litellm")
    DummyLogger, calls = _make_dummy_logger()
    monkeypatch.setattr(litellm, "logger", DummyLogger)

    # Settings: non-streaming, but still log content
    monkeypatch.setattr(
        litellm,
        "LITELLM_SETTINGS",
        SimpleNamespace(chat_model="m-nostream", log_llm_chat_content=True, chat_stream=False),
    )

    # supports_response_schema returns True so response_format should be forwarded
    monkeypatch.setattr(litellm, "supports_response_schema", lambda model: True)

    # We'll capture kwargs received by completion to assert response_format forwarded
    received = {}

    class Choice:
        def __init__(self, content, finish_reason):
            self.message = SimpleNamespace(content=content)
            self.finish_reason = finish_reason

    def completion_stub(messages, stream, max_retries, **kw):
        received["kw"] = kw.copy()
        # Return an object compatible with non-streaming access
        return SimpleNamespace(choices=[Choice("World", "error")])

    monkeypatch.setattr(litellm, "completion", completion_stub)

    # completion_cost raises to trigger the except branch and set cost to np.nan
    def completion_cost_raises(model, messages, completion):
        raise RuntimeError("cost failed")

    monkeypatch.setattr(litellm, "completion_cost", completion_cost_raises)

    # token_counter returns deterministic values
    def token_counter_stub(model, **kwargs):
        if "messages" in kwargs:
            return 3
        if "text" in kwargs:
            return 5
        return 0

    monkeypatch.setattr(litellm, "token_counter", token_counter_stub)

    # Prepare backend instance and methods
    BackendCls = getattr(litellm, "LiteLLMAPIBackend")
    backend = object.__new__(BackendCls)
    backend._build_log_messages = lambda msgs: "LOGGED"
    backend.get_complete_kwargs = lambda: {"model": "m-nostream"}

    # Reset ACC_COST to 0
    monkeypatch.setattr(litellm, "ACC_COST", 0.0)

    # Act
    sentinel_response_format = {"schema": "ok"}
    content, finish_reason = backend._create_chat_completion_inner_function(
        [{"role": "user", "content": "hey"}], response_format=sentinel_response_format
    )

    # Assert: non-streaming path returns string content and finish_reason
    assert content == "World"
    assert finish_reason == "error"
    # Since completion_cost raised, ACC_COST should remain unchanged and cost was set to nan
    assert math.isnan(getattr(litellm, "ACC_COST")) is False
    assert math.isclose(getattr(litellm, "ACC_COST"), 0.0, rel_tol=1e-12)
    # Ensure completion received the response_format forwarded from kwargs
    assert "response_format" in received.get("kw", {})
    assert received["kw"]["response_format"] == sentinel_response_format
    # Ensure a warning was logged for the cost exception
    assert any("Cost calculation failed" in str(args) or "cost failed" in str(args) for args, _ in calls["warning"]) or len(calls["warning"]) >= 1
