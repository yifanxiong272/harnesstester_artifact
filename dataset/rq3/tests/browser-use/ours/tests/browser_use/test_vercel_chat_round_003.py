import asyncio
import json
from types import SimpleNamespace
import pytest

import browser_use.llm.vercel.chat as chat_mod
from browser_use.llm.vercel.chat import ChatVercel
from browser_use.llm.exceptions import ModelProviderError

# Helpers: lightweight mocks that mirror the attributes used by the implementation
class MockMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content

    def model_copy(self, deep=False):
        # Return a shallow copy with same attributes (deep param accepted by code)
        return MockMessage(self.role, self.content)

class MockResponse:
    def __init__(self, content, finish_reason=None):
        message = SimpleNamespace(content=content)
        self.choices = [SimpleNamespace(message=message, finish_reason=finish_reason)]

class DummyClient:
    def __init__(self, response):
        class Completions:
            def __init__(self, response):
                self._response = response

            async def create(self, *args, **kwargs):
                return self._response

        self.chat = SimpleNamespace(completions=Completions(response))

class DummyOutputFormat:
    @staticmethod
    def model_validate(data):
        return {"validated": True, "data": data}

    @staticmethod
    def model_validate_json(text):
        return {"validated_json": True, "data": json.loads(text)}

# Small dummy classes to patch symbols used in the module under test
class DummyContentPartTextParam:
    def __init__(self, text):
        self.text = text

class DummySystemMessage:
    def __init__(self, content):
        self.role = "system"
        self.content = content

class DummyResponseFormatJSONSchema:
    def __init__(self, json_schema, type):
        self.json_schema = json_schema
        self.type = type

@pytest.fixture(autouse=True)
def patch_module_symbols(monkeypatch):
    recorded = {}

    def fake_serialize_messages(messages):
        recorded['last'] = messages
        return "VERCEL_MSGS"

    monkeypatch.setattr(chat_mod, 'VercelMessageSerializer', SimpleNamespace(serialize_messages=fake_serialize_messages))
    monkeypatch.setattr(chat_mod, 'SchemaOptimizer', SimpleNamespace(
        create_gemini_optimized_schema=lambda output_format: {"gemini": "schema"},
        create_optimized_json_schema=lambda output_format: {"optimized": "schema"}
    ))
    monkeypatch.setattr(chat_mod, 'ContentPartTextParam', DummyContentPartTextParam)
    monkeypatch.setattr(chat_mod, 'SystemMessage', DummySystemMessage)
    monkeypatch.setattr(chat_mod, 'ResponseFormatJSONSchema', DummyResponseFormatJSONSchema)

    yield recorded


def make_instance():
    """Create a ChatVercel instance without invoking full dataclass init; set attributes used by ainvoke."""
    inst = ChatVercel.__new__(ChatVercel)
    inst.temperature = None
    inst.max_tokens = None
    inst.top_p = None
    inst.provider_options = {}
    inst.reasoning = {}
    inst.reasoning_models = None
    inst.model_fallbacks = None
    inst.caching = None
    inst.model = "default-model"
    # Do not set inst.name; name is a read-only property that returns str(self.model).
    inst._get_usage = lambda response: {"usage": "ok"}
    return inst


def test_string_response_round_003(patch_module_symbols):
    inst = make_instance()
    inst.temperature = 0.2
    inst.max_tokens = 50
    inst.top_p = None
    inst.provider_options = {"prov": 1}
    inst.reasoning = {"anthropic": {"thinking": True}}
    inst.model_fallbacks = ["m1", "m2"]
    inst.caching = True

    messages = [MockMessage('user', 'hello')]

    resp = MockResponse("hi world", finish_reason="stop")
    inst.get_client = lambda: DummyClient(resp)

    result = asyncio.run(inst.ainvoke(messages, output_format=None))

    assert hasattr(result, 'completion')
    assert result.completion == "hi world"
    assert result.usage == {"usage": "ok"}
    assert result.stop_reason == "stop"


def test_gemini_json_parsing_with_backticks_round_003(patch_module_symbols):
    recorded = patch_module_symbols
    inst = make_instance()
    inst.model = "google/some-gemini"
    inst.reasoning_models = ["gemini"]
    inst.reasoning = {}

    messages = [MockMessage('system', 'system_instructions'), MockMessage('user', 'please respond')]

    content_json = '```json{"hello": "world"}```'
    resp = MockResponse(content_json, finish_reason="done")
    inst.get_client = lambda: DummyClient(resp)

    result = asyncio.run(inst.ainvoke(messages, output_format=DummyOutputFormat))

    assert 'last' in recorded
    modified_msgs = recorded['last']
    assert isinstance(modified_msgs, list)
    assert hasattr(modified_msgs[0], 'content')
    assert "IMPORTANT: You must respond with ONLY a valid JSON object" in str(modified_msgs[0].content)

    assert hasattr(result, 'completion')
    assert result.completion['validated'] is True
    assert result.completion['data'] == {"hello": "world"}
    assert result.usage == {"usage": "ok"}


def test_gemini_no_content_raises_round_003(patch_module_symbols):
    inst = make_instance()
    inst.model = "google/empty-response"
    inst.reasoning_models = ["empty"]
    inst.reasoning = {}

    messages = [MockMessage('user', 'anything')]

    resp = MockResponse(None, finish_reason=None)
    inst.get_client = lambda: DummyClient(resp)

    with pytest.raises(ModelProviderError):
        asyncio.run(inst.ainvoke(messages, output_format=DummyOutputFormat))


def test_non_reasoning_structured_json_schema_round_003(patch_module_symbols):
    inst = make_instance()
    inst.model = "openai/standard"
    inst.reasoning_models = ["unrelated-pattern"]
    inst.reasoning = {}

    messages = [MockMessage('user', 'please give structured output')]

    resp = MockResponse('{"alpha": 1}', finish_reason="ok")
    inst.get_client = lambda: DummyClient(resp)

    result = asyncio.run(inst.ainvoke(messages, output_format=DummyOutputFormat))

    assert result.completion == {"validated_json": True, "data": {"alpha": 1}}
    assert result.usage == {"usage": "ok"}
