import json
import types
import pytest
from types import SimpleNamespace

from browser_use.llm.deepseek import chat as chat_mod
from browser_use.llm.deepseek.chat import ChatDeepSeek, ModelProviderError, ChatInvokeCompletion

# Utilities for faking client responses
class FakeCompletions:
    def __init__(self, resp):
        self._resp = resp
        self._last_kwargs = None

    async def create(self, *args, **kwargs):
        # Record kwargs so tests can assert common fields were passed
        self._last_kwargs = kwargs
        return self._resp

class FakeClient:
    def __init__(self, resp):
        self.chat = SimpleNamespace(completions=FakeCompletions(resp))

# Dummy output_format classes used in tests
class DummyOutputFormat:
    # marker used by hasattr in code
    model_json_schema = True

    # __name__ used to build tool metadata
    __name__ = "DummyOutputFormat"

    @classmethod
    def model_validate(cls, parsed):
        # deterministic transformation for assertion
        return {"validated": parsed}

    @classmethod
    def model_validate_json(cls, content: str):
        # parse JSON string and wrap to show it was validated
        return {"validated_json": json.loads(content)}


@pytest.mark.asyncio
async def test_regular_text_round_014(monkeypatch):
    """
    Covers: regular multi-turn conversation path (output_format is None, no tools)
    - Ensures temperature/max_tokens/top_p/seed are forwarded to the client
    - Ensures beta prefix logic sets prefix on last assistant message
    - Ensures stop is forwarded
    """
    # Prepare ds_messages returned by serializer (last message is assistant)
    ds_messages = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "prev"}]
    monkeypatch.setattr(chat_mod.DeepSeekMessageSerializer, "serialize_messages", lambda messages: ds_messages)

    # Prepare fake response with simple text content
    msg = SimpleNamespace(content="hello world")
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    fake_client = FakeClient(resp)

    # Patch _client to return our fake client instance
    monkeypatch.setattr(ChatDeepSeek, "_client", lambda self: fake_client)

    # Construct ChatDeepSeek instance with values that will populate `common`
    inst = ChatDeepSeek()
    inst.temperature = 0.7
    inst.max_tokens = 123
    inst.top_p = 0.9
    inst.seed = 42
    inst.model = "m"
    # NOTE: do NOT assign to inst.name since it's a read-only property
    inst.base_url = "https://example.com/beta"

    # Provide a stop list to exercise the stop branch
    completion = await inst.ainvoke(messages=["ignored"], output_format=None, tools=None, stop=["STOP"])

    # Assertions on returned completion
    assert isinstance(completion, ChatInvokeCompletion)
    assert completion.completion == "hello world"

    # Ensure serializer mutated last assistant message to include prefix=True
    assert ds_messages[-1].get("prefix") is True

    # Ensure the client saw the common kwargs (temperature, max_tokens, top_p, seed, stop)
    last_kwargs = fake_client.chat.completions._last_kwargs
    assert last_kwargs is not None
    assert last_kwargs.get("temperature") == 0.7
    assert last_kwargs.get("max_tokens") == 123
    assert last_kwargs.get("top_p") == 0.9
    assert last_kwargs.get("seed") == 42
    # stop is passed only when base_url endswith('/beta') and stop provided
    assert last_kwargs.get("stop") == ["STOP"]


@pytest.mark.asyncio
async def test_function_call_with_output_format_model_round_014(monkeypatch):
    """
    Covers: function calling path when output_format is provided and tool_calls present
    - Ensures tool metadata is built via SchemaOptimizer.create_optimized_json_schema
    - Ensures raw JSON string arguments are json.loads'd and passed to output_format.model_validate
    """
    # messages serialization
    monkeypatch.setattr(chat_mod.DeepSeekMessageSerializer, "serialize_messages", lambda messages: [{"role": "user"}])

    # Patch SchemaOptimizer to return a predictable schema dict
    monkeypatch.setattr(chat_mod.SchemaOptimizer, "create_optimized_json_schema", lambda _arg: {"title": "X", "properties": {"a": {"type": "integer"}}})

    # Build a fake message with tool_calls containing JSON string arguments
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments='{"a": 1}'))
    message = SimpleNamespace(tool_calls=[tool_call])
    resp = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    fake_client = FakeClient(resp)
    monkeypatch.setattr(ChatDeepSeek, "_client", lambda self: fake_client)

    inst = ChatDeepSeek()
    inst.model = "m"
    # NOTE: do NOT assign to inst.name since it's a read-only property
    inst.base_url = None

    # Call with output_format set to our DummyOutputFormat class
    completion = await inst.ainvoke(messages=["x"], output_format=DummyOutputFormat, tools=None)

    # Should return validated object via DummyOutputFormat.model_validate
    assert isinstance(completion, ChatInvokeCompletion)
    assert completion.completion == {"validated": {"a": 1}}

    # And the client was invoked with tools and tool_choice in kwargs
    last_kwargs = fake_client.chat.completions._last_kwargs
    assert last_kwargs is not None
    assert "tools" in last_kwargs
    assert isinstance(last_kwargs.get("tools"), list)
    assert last_kwargs.get("tool_choice") == {"type": "function", "function": {"name": "DummyOutputFormat"}}


@pytest.mark.asyncio
async def test_tool_no_tool_calls_raises_round_014(monkeypatch):
    """
    Covers: branch where tool calling path gets a response without tool_calls, raising ValueError
    """
    monkeypatch.setattr(chat_mod.DeepSeekMessageSerializer, "serialize_messages", lambda messages: [{"role": "user"}])

    # Prepare a response where message has no tool_calls attr or it's falsy
    message = SimpleNamespace(tool_calls=None)
    resp = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    fake_client = FakeClient(resp)
    monkeypatch.setattr(ChatDeepSeek, "_client", lambda self: fake_client)

    inst = ChatDeepSeek()
    inst.model = "m"
    # NOTE: do NOT assign to inst.name

    with pytest.raises(ValueError, match="Expected tool_calls in response but got none"):
        await inst.ainvoke(messages=["x"], output_format=DummyOutputFormat, tools=None)


@pytest.mark.asyncio
async def test_function_call_no_output_format_returns_parsed_round_014(monkeypatch):
    """
    Covers: function calling path when tools are provided and output_format is None
    - Ensures non-string raw_args are used directly (parsed = raw_args) and returned
    """
    monkeypatch.setattr(chat_mod.DeepSeekMessageSerializer, "serialize_messages", lambda messages: [{"role": "user"}])

    # Make SchemaOptimizer a no-op if called
    monkeypatch.setattr(chat_mod.SchemaOptimizer, "create_optimized_json_schema", lambda _arg: {"properties": {}})

    # Create tool call where arguments are already a dict (not a string)
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments={"k": "v"}))
    message = SimpleNamespace(tool_calls=[tool_call])
    resp = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    fake_client = FakeClient(resp)
    monkeypatch.setattr(ChatDeepSeek, "_client", lambda self: fake_client)

    inst = ChatDeepSeek()
    inst.model = "m"
    # NOTE: do NOT assign to inst.name

    # Provide explicit tools to trigger function calling path even though output_format is None
    tools = [{"type": "function", "function": {"name": "tool1"}}]
    completion = await inst.ainvoke(messages=["x"], output_format=None, tools=tools)

    assert isinstance(completion, ChatInvokeCompletion)
    # Should return the parsed dict directly
    assert completion.completion == {"k": "v"}


@pytest.mark.asyncio
async def test_json_output_path_empty_content_raises_round_014(monkeypatch):
    """
    Covers: JSON output path where response.content is empty and triggers ModelProviderError
    """
    monkeypatch.setattr(chat_mod.DeepSeekMessageSerializer, "serialize_messages", lambda messages: [{"role": "user"}])

    # Build a response with empty content to trigger the empty-content branch
    message = SimpleNamespace(content="")
    resp = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    fake_client = FakeClient(resp)
    monkeypatch.setattr(ChatDeepSeek, "_client", lambda self: fake_client)

    inst = ChatDeepSeek()
    inst.model = "m"
    # NOTE: do NOT assign to inst.name

    with pytest.raises(ModelProviderError, match="Empty JSON content in DeepSeek response"):
        await inst.ainvoke(messages=["x"], output_format=DummyOutputFormat)
