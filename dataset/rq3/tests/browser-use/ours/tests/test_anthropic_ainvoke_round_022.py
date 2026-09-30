import asyncio
import json
from types import SimpleNamespace
import importlib
import pytest

# Module under test
m = importlib.import_module('browser_use.llm.anthropic.chat')

# Monkeypatch the class-level name property to be deterministic (read-only property exists in real class)
m.ChatAnthropic.name = property(lambda self: 'test-name')

# Helpers to produce a ChatAnthropic instance without running its __init__
def make_instance():
    inst = object.__new__(m.ChatAnthropic)
    # minimal attributes referenced by ainvoke
    inst.model = 'test-model'
    return inst

# Provide safe replacements for external symbols the module references when building tool params
m.AnthropicMessageSerializer = SimpleNamespace(serialize_messages=lambda messages: ([], None))
m.SchemaOptimizer = SimpleNamespace(create_optimized_json_schema=lambda t: {'title': getattr(t, '__name__', 'T'), 'properties': {}})
# Tool-related symbols - keep simple containers
m.ToolParam = lambda **kwargs: kwargs
m.CacheControlEphemeralParam = lambda **kwargs: kwargs
m.ToolChoiceToolParam = lambda **kwargs: kwargs
# omit sentinel used in calls
m.omit = object()
# Ensure Message is a type we can instantiate and use isinstance checks against
m.Message = type('Message', (), {})
# Replace ChatInvokeCompletion with a simple container so tests can introspect returned values
m.ChatInvokeCompletion = lambda **kwargs: SimpleNamespace(**kwargs)

# Test 1: output_format is None and _create_message returns a non-message -> ModelProviderError
def test_ainvoke_no_output_invalid_response_round_022():
    inst = make_instance()

    async def fake_create_message(**_kwargs):
        return 'not-a-message'

    inst._create_message = fake_create_message
    # ensure message-like detection returns False
    inst._is_message_like_response = lambda resp: False

    # call ainvoke and assert ModelProviderError is raised for unexpected response type
    with pytest.raises(m.ModelProviderError) as ei:
        asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=None))
    assert 'Unexpected response type' in str(ei.value) or 'Unexpected response type' in getattr(ei.value, 'message', '')


# Test 2: output_format is None and valid Message response -> returns ChatInvokeCompletion with expected fields
def test_ainvoke_no_output_success_round_022():
    inst = make_instance()

    class Resp(m.Message):
        def __init__(self):
            self.stop_reason = 'stop'
            # content not used in this path
            self.content = []

    resp = Resp()

    async def fake_create_message(**_kwargs):
        return resp

    inst._create_message = fake_create_message
    inst._is_message_like_response = lambda r: True
    inst._get_usage = lambda r: {'units': 1}
    inst._extract_content_blocks = lambda r: ('hello', None, None)
    inst._get_stop_details = lambda r: {'detail': 'd'}

    result = asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=None))
    assert getattr(result, 'completion') == 'hello'
    assert getattr(result, 'usage') == {'units': 1}
    assert getattr(result, 'stop_reason') == 'stop'
    assert getattr(result, 'stop_details') == {'detail': 'd'}


# Test 3: structured output where the model returns a tool_use block with input as JSON string
# The first model_validate call will raise when given a raw string, forcing the JSON reparsing path
def test_ainvoke_structured_tool_string_json_round_022():
    inst = make_instance()

    class Resp(m.Message):
        def __init__(self, content):
            self.stop_reason = 'sr'
            self.content = content

    # content block shaped like anthropic TextBlock / tool use
    class ContentBlock:
        def __init__(self, t, inp):
            self.type = t
            self.input = inp

    content_block = ContentBlock('tool_use', json.dumps({'x': 1}))
    resp = Resp([content_block])

    async def fake_create_message(**_kwargs):
        return resp

    inst._create_message = fake_create_message
    inst._is_message_like_response = lambda r: True
    inst._get_usage = lambda r: {'u': 'ok'}
    inst._get_stop_details = lambda r: {'sd': True}

    # Make an output_format with a model_validate that fails on raw strings, succeeds on dicts
    class OutFmt:
        __name__ = 'OutFmt'

        @staticmethod
        def model_validate(value):
            if isinstance(value, str):
                raise Exception('string not acceptable')
            # accept parsed dict
            return {'validated': value}

    # Ensure schema title removal branch is executed
    m.SchemaOptimizer = SimpleNamespace(create_optimized_json_schema=lambda t: {'title': 'T', 'properties': {}})

    result = asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=OutFmt))
    # After repair, we expect the validated dict returned as completion
    assert isinstance(result, SimpleNamespace)
    assert result.completion == {'validated': {'x': 1}}
    assert result.usage == {'u': 'ok'}
    assert result.stop_reason == 'sr'
    assert result.stop_details == {'sd': True}


# Test 4: structured output where tool_use input is a dict with a double-serialized string value
# This triggers the dict branch that attempts to json.loads fields that start with '{' or '['
def test_ainvoke_structured_tool_double_serialized_round_022():
    inst = make_instance()

    class Resp(m.Message):
        def __init__(self, content):
            self.stop_reason = 'sr2'
            self.content = content

    class ContentBlock:
        def __init__(self, t, inp):
            self.type = t
            self.input = inp

    # input is a dict with a string-valued field that itself is JSON
    inner_serialized = json.dumps({'inner': 2})
    content_input = {'k': inner_serialized}
    content_block = ContentBlock('tool_use', content_input)
    resp = Resp([content_block])

    async def fake_create_message(**_kwargs):
        return resp

    inst._create_message = fake_create_message
    inst._is_message_like_response = lambda r: True
    inst._get_usage = lambda r: {'u': 2}
    inst._get_stop_details = lambda r: {'sd': 2}

    # output_format that fails initially when given the original dict (to drive the repair path),
    # but succeeds after inner field is parsed into a nested dict
    class OutFmt2:
        __name__ = 'OutFmt2'

        @staticmethod
        def model_validate(value):
            # If k is still a str, fail to trigger repair logic
            if isinstance(value, dict) and isinstance(value.get('k'), str):
                raise Exception('still string')
            return {'validated': value}

    result = asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=OutFmt2))
    assert result.completion == {'validated': {'k': {'inner': 2}}}
    assert result.usage == {'u': 2}
    assert result.stop_reason == 'sr2'
    assert result.stop_details == {'sd': 2}


# Test 5: no tool_use found and _requires_auto_tool_choice is False -> ValueError
def test_ainvoke_structured_no_tool_use_raises_round_022():
    inst = make_instance()

    class Resp(m.Message):
        def __init__(self):
            self.stop_reason = None
            self.content = [SimpleNamespace(type='text', text='no tool here')]

    resp = Resp()

    async def fake_create_message(**_kwargs):
        return resp

    inst._create_message = fake_create_message
    inst._is_message_like_response = lambda r: True
    inst._requires_auto_tool_choice = lambda: False

    class DummyFmt:
        __name__ = 'DummyFmt'

    with pytest.raises(ValueError):
        asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=DummyFmt))


# Test 6: error mapping - RateLimitError from low-level client should raise ModelRateLimitError
def test_ainvoke_rate_limit_error_round_022():
    inst = make_instance()

    # Create a sentinel RateLimitError class with .message attribute to mimic upstream
    class RLExc(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    # Patch module's RateLimitError symbol
    m.RateLimitError = RLExc

    async def raising_create_message(**_kwargs):
        raise RLExc('too many requests')

    inst._create_message = raising_create_message

    with pytest.raises(m.ModelRateLimitError) as ei:
        asyncio.run(inst.ainvoke(messages=[SimpleNamespace()], output_format=None))
    # Ensure the ModelRateLimitError references the original message
    assert 'too many requests' in str(ei.value) or 'too many requests' in getattr(ei.value, 'message', '')
