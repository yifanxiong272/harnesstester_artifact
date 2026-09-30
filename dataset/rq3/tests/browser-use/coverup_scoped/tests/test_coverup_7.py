# file: browser_use/llm/litellm/chat.py:114-227
# asked: {"lines": [114, 116, 117, 118, 119, 120, 121, 122, 124, 126, 127, 128, 129, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 146, 147, 148, 149, 150, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 186, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 209, 210, 211, 212, 214, 215, 216, 217, 218, 219, 222, 223, 224, 225, 226], "branches": [[132, 133], [132, 134], [134, 135], [134, 136], [136, 137], [136, 138], [138, 139], [138, 140], [140, 141], [140, 143], [143, 144], [143, 154], [190, 191], [190, 197], [204, 205], [204, 207], [207, 208], [207, 222], [208, 209], [208, 214]]}
# gained: {"lines": [114, 117, 119, 120, 121, 122, 124, 126, 127, 128, 129, 132, 133, 134, 135, 136, 138, 140, 143, 144, 145, 146, 147, 148, 149, 150, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 180, 181, 182, 183, 184, 186, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 201, 202, 203, 204, 207, 208, 209, 210, 211, 212, 214, 215, 216, 217, 218, 219, 222, 223, 224, 225, 226], "branches": [[132, 133], [132, 134], [134, 135], [134, 136], [136, 138], [138, 140], [140, 143], [143, 144], [143, 154], [190, 191], [190, 197], [204, 207], [207, 208], [207, 222], [208, 209], [208, 214]]}

import sys
from types import ModuleType
import pytest
from dataclasses import dataclass
from pydantic import BaseModel

from browser_use.llm.litellm.chat import ChatLiteLLM
from browser_use.llm.litellm.serializer import LiteLLMMessageSerializer
from browser_use.llm.schema import SchemaOptimizer
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError


def _install_litellm(monkeypatch, acompletion_func, *, RateLimitError=Exception, Timeout=Exception, APIConnectionError=Exception, APIError=Exception):
    """
    Install fake litellm, litellm.exceptions, and litellm.types.utils.ModelResponse into sys.modules using monkeypatch.
    Returns the ModelResponse class we created.
    """
    litellm = ModuleType("litellm")
    litellm.acompletion = acompletion_func

    exc_mod = ModuleType("litellm.exceptions")
    exc_mod.RateLimitError = RateLimitError
    exc_mod.Timeout = Timeout
    exc_mod.APIConnectionError = APIConnectionError
    exc_mod.APIError = APIError

    types_mod = ModuleType("litellm.types")
    utils_mod = ModuleType("litellm.types.utils")

    @dataclass
    class ModelResponse:
        choices: list
        usage: dict | None = None

    utils_mod.ModelResponse = ModelResponse
    types_mod.utils = utils_mod
    litellm.types = types_mod

    # Use monkeypatch to set modules so they're cleaned up automatically
    monkeypatch.setitem(sys.modules, "litellm", litellm)
    monkeypatch.setitem(sys.modules, "litellm.exceptions", exc_mod)
    monkeypatch.setitem(sys.modules, "litellm.types", types_mod)
    monkeypatch.setitem(sys.modules, "litellm.types.utils", utils_mod)

    return ModelResponse


@pytest.mark.asyncio
async def test_ainvoke_returns_text_completion(monkeypatch):
    # Arrange: prepare acompletion to return a ModelResponse with a single choice containing text content.
    @dataclass
    class Msg:
        content: str
        reasoning_content: str | None = None

    @dataclass
    class Choice:
        message: Msg
        finish_reason: str | None = None

    async def acompletion(**params):
        ModelResponse = sys.modules["litellm.types.utils"].ModelResponse
        return ModelResponse(choices=[Choice(message=Msg(content="hello world"), finish_reason="stop")], usage={"tokens": 10})

    # Install fake litellm
    _install_litellm(monkeypatch, acompletion)

    # Ensure serializer.serialize is called and returns something
    called = {}
    def fake_serialize(messages):
        called['called'] = True
        return [{"role": "user", "content": "ignored"}]
    monkeypatch.setattr(LiteLLMMessageSerializer, "serialize", staticmethod(fake_serialize))

    # Create ChatLiteLLM and invoke
    llm = ChatLiteLLM(model="test-model", api_key=None, api_base=None, temperature=0.0, max_tokens=10, max_retries=1)

    result = await llm.ainvoke([], output_format=None)

    # Assert results
    assert called.get('called', False) is True
    assert result.completion == "hello world"
    assert result.stop_reason == "stop"
    assert result.thinking is None


@pytest.mark.asyncio
async def test_ainvoke_structured_output_parsed(monkeypatch):
    # Arrange: acompletion returns JSON string content for structured output
    @dataclass
    class Msg:
        content: str
        reasoning_content: str | None = None

    @dataclass
    class Choice:
        message: Msg
        finish_reason: str | None = None

    async def acompletion(**params):
        ModelResponse = sys.modules["litellm.types.utils"].ModelResponse
        return ModelResponse(choices=[Choice(message=Msg(content='{"key": "value"}'), finish_reason="stop")], usage=None)

    _install_litellm(monkeypatch, acompletion)

    # Patch serializer and schema optimizer
    monkeypatch.setattr(LiteLLMMessageSerializer, "serialize", staticmethod(lambda msgs: [{"role":"user","content":"? "}]))

    monkeypatch.setattr(SchemaOptimizer, "create_optimized_json_schema", staticmethod(lambda t: {"dummy": True}))

    # Define a pydantic model for structured output and have model_validate_json return an instance of it
    class ParsedModel(BaseModel):
        key: str

    class OutputFormat:
        @classmethod
        def model_validate_json(cls, json_str):
            import json
            data = json.loads(json_str)
            return ParsedModel(**data)

    llm = ChatLiteLLM(model="m", api_key=None, api_base=None, temperature=None, max_tokens=None, max_retries=1)

    result = await llm.ainvoke([], output_format=OutputFormat)

    comp = result.completion
    # comp should be an instance of ParsedModel (pydantic BaseModel subclass)
    assert isinstance(comp, ParsedModel)
    # Use pydantic v2 or v1 methods to extract data
    if hasattr(comp, "model_dump") and callable(getattr(comp, "model_dump")):
        assert comp.model_dump() == {"key": "value"}
    else:
        assert comp.dict() == {"key": "value"}

    assert result.stop_reason == "stop"


@pytest.mark.asyncio
async def test_ainvoke_structured_output_empty_content_raises(monkeypatch):
    # Arrange: acompletion returns empty content while output_format is requested
    @dataclass
    class Msg:
        content: str
        reasoning_content: str | None = None

    @dataclass
    class Choice:
        message: Msg
        finish_reason: str | None = None

    async def acompletion(**params):
        ModelResponse = sys.modules["litellm.types.utils"].ModelResponse
        return ModelResponse(choices=[Choice(message=Msg(content=""), finish_reason="stop")], usage=None)

    _install_litellm(monkeypatch, acompletion)

    monkeypatch.setattr(LiteLLMMessageSerializer, "serialize", staticmethod(lambda msgs: []))
    monkeypatch.setattr(SchemaOptimizer, "create_optimized_json_schema", staticmethod(lambda t: {}))

    class OutputFormat:
        @classmethod
        def model_validate_json(cls, json_str):
            return {}

    llm = ChatLiteLLM(model="m", api_key=None, api_base=None, temperature=None, max_tokens=None, max_retries=1)

    with pytest.raises(ModelProviderError) as excinfo:
        await llm.ainvoke([], output_format=OutputFormat)
    assert "Model returned empty content for structured output request" in str(excinfo.value)
    assert getattr(excinfo.value, "status_code", None) == 500


@pytest.mark.asyncio
async def test_ainvoke_empty_choices_raises(monkeypatch):
    # Arrange: acompletion returns a ModelResponse with no choices
    async def acompletion(**params):
        ModelResponse = sys.modules["litellm.types.utils"].ModelResponse
        return ModelResponse(choices=[], usage=None)

    _install_litellm(monkeypatch, acompletion)

    monkeypatch.setattr(LiteLLMMessageSerializer, "serialize", staticmethod(lambda msgs: []))

    llm = ChatLiteLLM(model="m", api_key=None, api_base=None, temperature=None, max_tokens=None, max_retries=1)

    with pytest.raises(ModelProviderError) as excinfo:
        await llm.ainvoke([], output_format=None)
    assert "Empty response: no choices returned by the model" in str(excinfo.value)
    assert getattr(excinfo.value, "status_code", None) == 502


@pytest.mark.asyncio
async def test_ainvoke_rate_limit_and_api_errors_and_timeout_and_generic(monkeypatch):
    # We'll test several exception branches by installing litellm that raises different exceptions each call.

    # Create custom exception classes to match what ainvoke expects
    class RateLimitError(Exception):
        pass

    class TimeoutError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    class APIError(Exception):
        def __init__(self, msg="api err", status_code=None):
            super().__init__(msg)
            self.status_code = status_code

    # Helper to run one scenario
    async def do_scenario(raise_exc):
        async def _acompletion(**params):
            raise raise_exc

        _install_litellm(monkeypatch, _acompletion, RateLimitError=RateLimitError, Timeout=TimeoutError, APIConnectionError=APIConnectionError, APIError=APIError)
        monkeypatch.setattr(LiteLLMMessageSerializer, "serialize", staticmethod(lambda msgs: []))
        llm = ChatLiteLLM(model="m", api_key=None, api_base=None, temperature=None, max_tokens=None, max_retries=1)
        with pytest.raises(Exception) as ei:
            await llm.ainvoke([], output_format=None)
        return ei.value

    # RateLimitError should be converted to ModelRateLimitError
    exc = await do_scenario(RateLimitError("rate limited"))
    assert isinstance(exc, ModelRateLimitError)

    # Timeout should become ModelProviderError with message containing 'Request timed out'
    exc = await do_scenario(TimeoutError("timeout happened"))
    assert isinstance(exc, ModelProviderError)
    assert "Request timed out" in str(exc)

    # APIConnectionError becomes ModelProviderError
    exc = await do_scenario(APIConnectionError("conn failed"))
    assert isinstance(exc, ModelProviderError)
    assert "conn failed" in str(exc)

    # APIError with falsy status_code (0) should result in status_code 502
    api_err = APIError("bad api", status_code=0)
    exc = await do_scenario(api_err)
    assert isinstance(exc, ModelProviderError)
    assert getattr(exc, "status_code", None) == 502

    # Generic Exception should be wrapped as ModelProviderError
    exc = await do_scenario(Exception("boom"))
    assert isinstance(exc, ModelProviderError)
    assert "boom" in str(exc)
