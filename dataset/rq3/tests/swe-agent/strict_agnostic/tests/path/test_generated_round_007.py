import types
import pytest
from types import SimpleNamespace

import litellm
from sweagent.agent import models
from sweagent.exceptions import (
    ContextWindowExceededError,
    ModelConfigurationError,
)


class _DummyLogger:
    def __init__(self):
        self.records = {"warning": [], "info": [], "debug": [], "error": []}

    def warning(self, msg):
        self.records["warning"].append(str(msg))

    def info(self, msg):
        self.records["info"].append(str(msg))

    def debug(self, msg):
        self.records["debug"].append(str(msg))

    def error(self, msg):
        self.records["error"].append(str(msg))


class _FakeToolCall:
    def __init__(self, name="t"):
        self._name = name

    def to_dict(self):
        return {"tool": self._name}


class _FakeMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeResponse:
    def __init__(self, choices):
        self.choices = choices


class _FakeConfig:
    def __init__(self):
        self.name = "test-model"
        self.temperature = 0.0
        self.top_p = 1.0
        self.api_version = None
        self._api_key = "fake"
        self.fallbacks = None
        self.completion_kwargs = {}
        self.api_base = "http://example.local"
        self.per_instance_cost_limit = 0
        self.total_cost_limit = 0

    def choose_api_key(self):
        return self._api_key


class _FakeTools:
    def __init__(self, use_function_calling=False):
        self.use_function_calling = use_function_calling
        self.tools = [{"name": "t1"}]


class _FakeModelInstance:
    # Provide the attributes accessed by LiteLLMModel._single_query
    def __init__(self):
        self._sleep = lambda: None
        self.config = _FakeConfig()
        self.model_max_input_tokens = None
        self.model_max_output_tokens = 5
        self.logger = _DummyLogger()
        self.lm_provider = "anthropic"
        self.tools = _FakeTools(use_function_calling=True)
        self._stats = {}

    def _update_stats(self, input_tokens, output_tokens, cost):
        # record for assertions
        self._stats.update({"in": input_tokens, "out": output_tokens, "cost": cost})


def _bind_single_query(fake):
    # bind the unbound function to fake instance
    func = models.LiteLLMModel._single_query
    return func.__get__(fake, fake.__class__)


def _install_default_litellm_mocks(monkeypatch, captured):
    # token_counter differentiates messages vs text
    def token_counter(messages=None, text=None, model=None):
        if messages is not None:
            # small deterministic input tokens
            return 2
        if text is not None:
            # deterministic output token count based on length
            return max(1, len(text))
        return 0

    monkeypatch.setattr(litellm, "utils", SimpleNamespace(token_counter=token_counter))

    # ensure exceptions namespace exists and contains classes we need
    exc_ns = SimpleNamespace(
        ContextWindowExceededError=type("LLMContextWindowExceeded", (Exception,), {}),
        ContentPolicyViolationError=type("LLMContentPolicy", (Exception,), {}),
        BadRequestError=type("LLMBadRequest", (Exception,), {}),
    )
    monkeypatch.setattr(litellm, "exceptions", exc_ns)

    # default completion does a simple return and records kwargs
    def completion_mock(*_, **kwargs):
        captured["completion_kwargs"] = kwargs
        msg = _FakeMessage("hello", tool_calls=[_FakeToolCall("tool1")])
        choices = [_FakeChoice(msg)]
        return _FakeResponse(choices)

    monkeypatch.setattr(litellm, "completion", completion_mock)

    class CostCalc:
        @staticmethod
        def completion_cost(response):
            return 0.42

    monkeypatch.setattr(litellm, "cost_calculator", CostCalc)


def test_cache_control_and_anthropic_and_tool_calls_round_007(monkeypatch):
    """
    Exercise branches that remove cache_control (lines ~658-659), set anthropic max_tokens (678-679),
    pass api_base (671-673) and produce tool_calls in the response (724-725).
    """
    captured = {}
    _install_default_litellm_mocks(monkeypatch, captured)

    fake = _FakeModelInstance()
    # set model_max_input_tokens to None to hit the warning branch
    fake.model_max_input_tokens = None

    # prepare messages including cache_control which should be deleted
    messages = [{"role": "user", "content": "hey", "cache_control": "no-cache"}]

    bound = _bind_single_query(fake)

    outputs = bound(messages=messages, n=None, temperature=None)

    # cache_control should be removed before calling token_counter => original messages unchanged by caller
    # but we can assert that the completion was invoked and api_base was forwarded
    assert isinstance(outputs, list)
    assert outputs[0]["message"] == "hello"
    # tool_calls should be present because tools.use_function_calling is True
    assert "tool_calls" in outputs[0]
    assert outputs[0]["tool_calls"] == [{"tool": "tool1"}]

    # the config.completion_kwargs should have been mutated to include max_tokens (anthropic)
    assert fake.config.completion_kwargs.get("max_tokens") == fake.model_max_output_tokens

    # ensure litellm.completion received api_base (extra_args path taken)
    assert "api_base" in captured.get("completion_kwargs", {}), "api_base should be forwarded to litellm.completion"

    # stats were updated with numeric cost and token counts
    assert fake._stats["cost"] == pytest.approx(0.42)
    assert fake._stats["in"] >= 0
    assert fake._stats["out"] >= 0


def test_badrequest_raises_context_window_exceeded_round_007(monkeypatch):
    """
    If litellm.completion raises a BadRequestError containing the phrase
    "is longer than the model's context length", LiteLLMModel._single_query should raise
    sweagent.exceptions.ContextWindowExceededError (mapping branch 698->699).
    """
    captured = {}

    # token_counter normal
    def token_counter(messages=None, text=None, model=None):
        return 1

    monkeypatch.setattr(litellm, "utils", SimpleNamespace(token_counter=token_counter))

    # create an exception type and ensure litellm.exceptions.BadRequestError references it
    BadReq = type("LLMBadRequest", (Exception,), {})
    monkeypatch.setattr(litellm, "exceptions", SimpleNamespace(BadRequestError=BadReq, ContextWindowExceededError=BadReq, ContentPolicyViolationError=BadReq))

    # completion raises the bad request with the specific substring
    def completion_raises(*_, **__):
        raise BadReq("model is longer than the model's context length: is longer than the model's context length")

    monkeypatch.setattr(litellm, "completion", completion_raises)

    fake = _FakeModelInstance()
    # ensure we don't trip input size raises earlier
    fake.model_max_input_tokens = 1000
    bound = _bind_single_query(fake)

    with pytest.raises(ContextWindowExceededError):
        bound(messages=[{"role": "user", "content": "x"}], n=None, temperature=None)


def test_cost_calculation_exception_with_limits_raises_model_config_error_round_007(monkeypatch):
    """
    When litellm.cost_calculator.completion_cost raises, and per_instance_cost_limit>0 or total_cost_limit>0
    the code should log an error and raise ModelConfigurationError (lines ~706-713).
    """
    captured = {}
    _install_default_litellm_mocks(monkeypatch, captured)

    # make the cost calculator raise
    def cost_raises(response):
        raise RuntimeError("cost boom")

    monkeypatch.setattr(litellm, "cost_calculator", SimpleNamespace(completion_cost=cost_raises))

    fake = _FakeModelInstance()
    # set cost limits to positive to trigger the raise branch
    fake.config.per_instance_cost_limit = 1
    fake.config.total_cost_limit = 0
    fake.model_max_input_tokens = 1000

    bound = _bind_single_query(fake)

    with pytest.raises(ModelConfigurationError):
        bound(messages=[{"role": "user", "content": "hello"}], n=None, temperature=None)
