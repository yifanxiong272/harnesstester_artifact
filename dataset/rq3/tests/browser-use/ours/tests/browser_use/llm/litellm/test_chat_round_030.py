import sys
import types
import asyncio
from types import SimpleNamespace
import pytest

import browser_use.llm.litellm.chat as chat
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError


# Helper to inject a fake `litellm` package with configurable acompletion and exception classes
class FakeModelResponse:
    def __init__(self, choices):
        self.choices = choices

class FakeChoice:
    def __init__(self, content, finish_reason=None, reasoning_content=None):
        self.message = SimpleNamespace(content=content, reasoning_content=reasoning_content)
        self.finish_reason = finish_reason


def install_fake_litellm(acompletion_func, *, APIError_cls=None, APIConnectionError_cls=None, RateLimitError_cls=None, Timeout_cls=None):
    # Build module hierarchy: litellm, litellm.exceptions, litellm.types, litellm.types.utils
    litellm_mod = types.ModuleType("litellm")
    litellm_mod.acompletion = acompletion_func

    # Default exception classes if not provided
    if APIError_cls is None:
        class APIError(Exception):
            def __init__(self, msg="api error", status_code=None):
                super().__init__(msg)
                self.status_code = status_code
        APIError_cls = APIError
    if APIConnectionError_cls is None:
        class APIConnectionError(Exception):
            pass
        APIConnectionError_cls = APIConnectionError
    if RateLimitError_cls is None:
        class RateLimitError(Exception):
            pass
        RateLimitError_cls = RateLimitError
    if Timeout_cls is None:
        class Timeout(Exception):
            pass
        Timeout_cls = Timeout

    # Put exceptions on a dedicated submodule so `from litellm.exceptions import ...` works
    exceptions_mod = types.ModuleType("litellm.exceptions")
    exceptions_mod.APIError = APIError_cls
    exceptions_mod.APIConnectionError = APIConnectionError_cls
    exceptions_mod.RateLimitError = RateLimitError_cls
    exceptions_mod.Timeout = Timeout_cls

    # types and utils modules for ModelResponse resolution
    types_mod = types.ModuleType("litellm.types")
    utils_mod = types.ModuleType("litellm.types.utils")
    utils_mod.ModelResponse = FakeModelResponse

    # Register modules in sys.modules
    sys.modules["litellm"] = litellm_mod
    sys.modules["litellm.exceptions"] = exceptions_mod
    sys.modules["litellm.types"] = types_mod
    sys.modules["litellm.types.utils"] = utils_mod

    return litellm_mod


def remove_fake_litellm():
    for key in ("litellm", "litellm.exceptions", "litellm.types", "litellm.types.utils"):
        if key in sys.modules:
            del sys.modules[key]


@pytest.mark.asyncio
async def test_success_plain_round_030():
    captured = {}

    async def fake_acompletion(**kwargs):
        # capture params to assert they were passed through
        captured.update(kwargs)
        # return a ModelResponse instance (from our fake litellm.types.utils)
        return FakeModelResponse([
            FakeChoice(content="hello world", finish_reason="stop", reasoning_content=None)
        ])

    install_fake_litellm(fake_acompletion)

    # Patch serializer and schema optimizer on chat module to deterministic behaviors
    orig_serializer = chat.LiteLLMMessageSerializer
    orig_schema = chat.SchemaOptimizer
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        chat.SchemaOptimizer = SimpleNamespace(create_optimized_json_schema=lambda t: {"dummy": True})

        # Prepare fake self with attributes the method uses
        fake_self = SimpleNamespace(
            model="gpt-test",
            max_retries=2,
            temperature=0.7,
            max_tokens=50,
            api_key="sk-xxx",
            api_base="https://api.example",
            metadata={"k": "v"},
            name="gpt-test-name",
            _parse_usage=lambda resp: {"parsed": True},
        )

        result = await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=None)

        # Assertions on observable output
        assert result.completion == "hello world"
        assert result.stop_reason == "stop"
        assert result.thinking is None

        # Ensure acompletion was invoked with expected keys
        assert captured.get("model") == "gpt-test"
        assert captured.get("messages") == [{"role": "user", "content": "hi"}]
        assert captured.get("num_retries") == 2
        assert captured.get("temperature") == 0.7
        assert captured.get("max_tokens") == 50
        assert captured.get("api_key") == "sk-xxx"
        assert captured.get("api_base") == "https://api.example"
        assert captured.get("metadata") == {"k": "v"}

    finally:
        # restore
        chat.LiteLLMMessageSerializer = orig_serializer
        chat.SchemaOptimizer = orig_schema
        remove_fake_litellm()


@pytest.mark.asyncio
async def test_success_structured_round_030():
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        # return JSON content string that will be parsed by output_format.model_validate_json
        return FakeModelResponse([
            FakeChoice(content='{"value": 123}', finish_reason="stop")
        ])

    install_fake_litellm(fake_acompletion)

    orig_serializer = chat.LiteLLMMessageSerializer
    orig_schema = chat.SchemaOptimizer
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        # Ensure schema creation is called but value not used directly in this test
        chat.SchemaOptimizer = SimpleNamespace(create_optimized_json_schema=lambda t: {"type": "object"})

        # Fake output_format type with model_validate_json method
        class FakeOutput:
            @staticmethod
            def model_validate_json(s: str):
                # return a Python object representing parsed structured content
                import json
                return json.loads(s)

        fake_self = SimpleNamespace(
            model="gpt-test-structured",
            max_retries=1,
            temperature=None,
            max_tokens=None,
            api_key=None,
            api_base=None,
            metadata=None,
            name="gpt-structured",
            _parse_usage=lambda resp: {"parsed": True},
        )

        result = await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=FakeOutput)

        # Structured output should be the parsed object (dict)
        assert isinstance(result.completion, dict)
        assert result.completion["value"] == 123
        assert result.stop_reason == "stop"

    finally:
        chat.LiteLLMMessageSerializer = orig_serializer
        chat.SchemaOptimizer = orig_schema
        remove_fake_litellm()


@pytest.mark.asyncio
async def test_structured_empty_content_raises_round_030():
    async def fake_acompletion(**kwargs):
        return FakeModelResponse([
            FakeChoice(content="", finish_reason=None)
        ])

    install_fake_litellm(fake_acompletion)

    orig_serializer = chat.LiteLLMMessageSerializer
    orig_schema = chat.SchemaOptimizer
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        chat.SchemaOptimizer = SimpleNamespace(create_optimized_json_schema=lambda t: {"type": "object"})

        class FakeOutput:
            @staticmethod
            def model_validate_json(s: str):
                return {"should": "not be used"}

        fake_self = SimpleNamespace(
            model="m",
            max_retries=0,
            temperature=None,
            max_tokens=None,
            api_key=None,
            api_base=None,
            metadata=None,
            name="m",
            _parse_usage=lambda resp: None,
        )

        with pytest.raises(ModelProviderError) as excinfo:
            await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=FakeOutput)

        # confirm message explains empty structured content
        assert "Model returned empty content for structured output request" in str(excinfo.value)

    finally:
        chat.LiteLLMMessageSerializer = orig_serializer
        chat.SchemaOptimizer = orig_schema
        remove_fake_litellm()


@pytest.mark.asyncio
async def test_exception_mapping_round_030():
    # Test RateLimitError -> ModelRateLimitError
    class RLExc(Exception):
        pass

    async def raise_rate(**kwargs):
        raise RLExc("too many requests")

    # Provide RLExc as litellm.RateLimitError so the except block triggers
    install_fake_litellm(raise_rate, RateLimitError_cls=RLExc)
    orig_serializer = chat.LiteLLMMessageSerializer
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        fake_self = SimpleNamespace(
            model="m",
            max_retries=0,
            temperature=None,
            max_tokens=None,
            api_key=None,
            api_base=None,
            metadata=None,
            name="m-name",
            _parse_usage=lambda resp: None,
        )

        with pytest.raises(ModelRateLimitError) as excinfo:
            await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=None)
        assert "too many requests" in str(excinfo.value)

    finally:
        chat.LiteLLMMessageSerializer = orig_serializer
        remove_fake_litellm()

    # Test APIError mapping status_code propagation and defaulting
    class MyAPIError(Exception):
        def __init__(self, msg, status_code=None):
            super().__init__(msg)
            self.status_code = status_code

    async def raise_api_with_status(**kwargs):
        raise MyAPIError("bad request", status_code=400)

    install_fake_litellm(raise_api_with_status, APIError_cls=MyAPIError)
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        with pytest.raises(ModelProviderError) as ei:
            await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=None)
        # status_code should be propagated
        assert getattr(ei.value, "status_code", None) == 400
    finally:
        chat.LiteLLMMessageSerializer = orig_serializer
        remove_fake_litellm()

    # Test APIError with falsy status (0 or None) results in default 502
    async def raise_api_falsy(**kwargs):
        raise MyAPIError("weird", status_code=0)

    install_fake_litellm(raise_api_falsy, APIError_cls=MyAPIError)
    try:
        chat.LiteLLMMessageSerializer = SimpleNamespace(serialize=lambda msgs: [{"role": "user", "content": "hi"}])
        with pytest.raises(ModelProviderError) as ei2:
            await chat.ChatLiteLLM.ainvoke(fake_self, messages=[SimpleNamespace(content="hi")], output_format=None)
        # falsy status becomes 502 due to `or 502` in code
        assert getattr(ei2.value, "status_code", None) == 502
    finally:
        chat.LiteLLMMessageSerializer = orig_serializer
        remove_fake_litellm()
