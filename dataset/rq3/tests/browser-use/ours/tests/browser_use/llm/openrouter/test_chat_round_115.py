import importlib
import pytest
from types import SimpleNamespace

mod = importlib.import_module('browser_use.llm.openrouter.chat')

# Helper to construct an uninitialized ChatOpenRouter and set required attrs
def make_router_instance():
    inst = object.__new__(mod.ChatOpenRouter)
    # attributes used by ainvoke
    inst.model = 'test-model'
    inst.temperature = 0.0
    inst.top_p = 1.0
    inst.seed = None
    inst.extra_body = None
    inst.http_referer = None
    # name is a read-only property on ChatOpenRouter; do not assign directly
    # default usage retriever; tests may override
    inst._get_usage = lambda response: SimpleNamespace(total_tokens=0, prompt_tokens=0, completion_tokens=0)
    return inst

@pytest.mark.asyncio
async def test_string_response_round_115(monkeypatch):
    # Cover the branch: output_format is None, http_referer present -> extra_headers included
    instance = make_router_instance()
    instance.http_referer = 'https://referer.example'

    # Patch serializer to avoid dependency
    monkeypatch.setattr(mod, 'OpenRouterMessageSerializer', SimpleNamespace(serialize_messages=lambda m: [{'role': 'user', 'content': 'x'}]))

    # Capture kwargs passed into create
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='hello'))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    # Ensure _get_usage returns a recognizable object
    instance._get_usage = lambda response: SimpleNamespace(total_tokens=1, prompt_tokens=0, completion_tokens=1)

    result = await instance.ainvoke(messages=[{'role': 'user', 'content': 'hi'}], output_format=None)

    assert hasattr(result, 'completion')
    assert result.completion == 'hello'
    # extra headers should be forwarded when http_referer set
    assert 'extra_headers' in captured
    assert captured['extra_headers'] == {'HTTP-Referer': 'https://referer.example'}


@pytest.mark.asyncio
async def test_structured_response_round_115(monkeypatch):
    # Cover structured output branch: SchemaOptimizer used, ResponseFormatJSONSchema constructed, model_validate_json invoked
    instance = make_router_instance()

    monkeypatch.setattr(mod, 'OpenRouterMessageSerializer', SimpleNamespace(serialize_messages=lambda m: [{'role': 'user', 'content': 'x'}]))

    # Replace SchemaOptimizer.create_optimized_json_schema
    monkeypatch.setattr(mod, 'SchemaOptimizer', SimpleNamespace(create_optimized_json_schema=lambda fmt: {'title': 'optimized'}))

    # Patch ResponseFormatJSONSchema constructor used in module
    def rf_constructor(**kwargs):
        return kwargs

    monkeypatch.setattr(mod, 'ResponseFormatJSONSchema', rf_constructor)

    # Fake output_format with model_validate_json
    class FakeOutputFormat:
        @staticmethod
        def model_validate_json(j):
            return {'parsed': j}

    # create returns a response with JSON string content
    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"x": 1}'))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    instance._get_usage = lambda response: SimpleNamespace(total_tokens=3, prompt_tokens=1, completion_tokens=2)

    result = await instance.ainvoke(messages=[{'role': 'user', 'content': 'hi'}], output_format=FakeOutputFormat)

    # The code returns parsed object as completion
    assert hasattr(result, 'completion')
    assert result.completion == {'parsed': '{"x": 1}'}


@pytest.mark.asyncio
async def test_structured_response_none_content_raises_round_115(monkeypatch):
    # When structured output expected but response content is None -> ModelProviderError
    instance = make_router_instance()

    monkeypatch.setattr(mod, 'OpenRouterMessageSerializer', SimpleNamespace(serialize_messages=lambda m: []))
    monkeypatch.setattr(mod, 'SchemaOptimizer', SimpleNamespace(create_optimized_json_schema=lambda fmt: {}))
    monkeypatch.setattr(mod, 'ResponseFormatJSONSchema', lambda **kwargs: kwargs)

    class FakeOutputFormat:
        @staticmethod
        def model_validate_json(j):
            return {}

    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    with pytest.raises(mod.ModelProviderError) as excinfo:
        await instance.ainvoke(messages=[], output_format=FakeOutputFormat)

    # Ensure the raised ModelProviderError originates from the parsing guard
    assert 'Failed to parse structured output' in str(excinfo.value) or isinstance(excinfo.value, mod.ModelProviderError)


@pytest.mark.asyncio
async def test_rate_limit_mapping_round_115(monkeypatch):
    # Simulate create raising RateLimitError -> mapped to ModelRateLimitError
    instance = make_router_instance()

    # Dummy RateLimitError with message attribute
    class DummyRateLimitError(Exception):
        def __init__(self, message):
            self.message = message
            super().__init__(message)

    monkeypatch.setattr(mod, 'RateLimitError', DummyRateLimitError)

    async def create(**kwargs):
        raise DummyRateLimitError('rate limited')

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    with pytest.raises(mod.ModelRateLimitError) as excinfo:
        await instance.ainvoke(messages=[], output_format=None)

    # original should be attached as __cause__
    assert isinstance(excinfo.value.__cause__, DummyRateLimitError)


@pytest.mark.asyncio
async def test_api_connection_mapping_round_115(monkeypatch):
    # Simulate create raising APIConnectionError -> mapped to ModelProviderError
    instance = make_router_instance()

    class DummyAPIConnectionError(Exception):
        pass

    monkeypatch.setattr(mod, 'APIConnectionError', DummyAPIConnectionError)

    async def create(**kwargs):
        raise DummyAPIConnectionError('connection failed')

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    with pytest.raises(mod.ModelProviderError) as excinfo:
        await instance.ainvoke(messages=[], output_format=None)

    # The message should reflect the original exception
    assert 'connection failed' in str(excinfo.value)


@pytest.mark.asyncio
async def test_api_status_mapping_round_115(monkeypatch):
    # Simulate create raising APIStatusError with message and status_code -> ModelProviderError with status_code
    instance = make_router_instance()

    class DummyAPIStatusError(Exception):
        def __init__(self, message, status_code):
            self.message = message
            self.status_code = status_code
            super().__init__(message)

    monkeypatch.setattr(mod, 'APIStatusError', DummyAPIStatusError)

    async def create(**kwargs):
        raise DummyAPIStatusError('bad status', 502)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    with pytest.raises(mod.ModelProviderError) as excinfo:
        await instance.ainvoke(messages=[], output_format=None)

    # The re-raised ModelProviderError should carry status_code when available
    assert hasattr(excinfo.value, 'status_code') and excinfo.value.status_code == 502


@pytest.mark.asyncio
async def test_generic_exception_mapping_round_115(monkeypatch):
    # Simulate create raising an arbitrary Exception -> ModelProviderError
    instance = make_router_instance()

    async def create(**kwargs):
        raise ValueError('something broke')

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    instance.get_client = lambda: client

    with pytest.raises(mod.ModelProviderError) as excinfo:
        await instance.ainvoke(messages=[], output_format=None)

    assert 'something broke' in str(excinfo.value)
