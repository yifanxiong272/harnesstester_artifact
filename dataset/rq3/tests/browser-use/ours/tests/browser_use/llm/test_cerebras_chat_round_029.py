import asyncio
from types import SimpleNamespace
import re
import pytest

from browser_use.llm.cerebras import chat as chat_mod
from browser_use.llm.cerebras.chat import ChatCerebras, ModelProviderError, ModelRateLimitError


class _FakeUsage:
    def __init__(self, prompt_tokens=1, completion_tokens=2, total_tokens=3):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content, usage=None):
        self.choices = [_FakeChoice(content)]
        self.usage = usage


class FakeClient:
    def __init__(self, to_return=None, to_raise=None):
        self._to_return = to_return
        self._to_raise = to_raise
        self.last_call_args = None

        class Completions:
            pass

        class Chat:
            pass

        self.chat = SimpleNamespace()
        self.chat.completions = SimpleNamespace()

        async def create(*args, **kwargs):
            # record what was passed in for later inspection
            self.last_call_args = {'args': args, 'kwargs': kwargs}
            if self._to_raise:
                raise self._to_raise
            return self._to_return

        # bind to this instance so tests can inspect last_call_args
        create_closure = create
        # Put create on nested namespace
        self.chat.completions.create = create_closure


class DummyRateLimitError(Exception):
    pass


@pytest.mark.asyncio
async def test_text_completion_success_round_029(monkeypatch):
    """Text path: successful completion returns text and usage."""
    # Arrange
    # Patch serializer to return a canned cerebras message structure
    monkeypatch.setattr(chat_mod, 'CerebrasMessageSerializer', SimpleNamespace(serialize_messages=lambda msgs: [{'role': 'user', 'content': 'hi'}]))

    usage = _FakeUsage(5, 6, 11)
    resp = _FakeResponse('hello world', usage=usage)
    fake_client = FakeClient(to_return=resp)

    # Patch _client to return our fake client
    monkeypatch.setattr(ChatCerebras, '_client', lambda self: fake_client)

    model = ChatCerebras()
    # Ensure at least one generation param flows into common
    model.temperature = 0.7
    model.top_p = None
    model.seed = None

    # Act
    result = await model.ainvoke(messages=[SimpleNamespace()] , output_format=None)

    # Assert
    assert result.completion == 'hello world'
    assert result.usage is not None
    assert result.usage.prompt_tokens == 5
    assert result.usage.completion_tokens == 6
    assert result.usage.total_tokens == 11
    # Verify the fake client was called with expected model kwarg and messages
    assert fake_client.last_call_args is not None
    assert fake_client.last_call_args['kwargs']['model'] == model.model
    assert isinstance(fake_client.last_call_args['kwargs']['messages'], list)


@pytest.mark.asyncio
async def test_text_completion_rate_limit_maps_to_model_rate_limit_error_round_029(monkeypatch):
    """If the underlying client raises a RateLimitError, it is translated to ModelRateLimitError."""
    # Arrange
    # Patch serializer
    monkeypatch.setattr(chat_mod, 'CerebrasMessageSerializer', SimpleNamespace(serialize_messages=lambda msgs: [{'role': 'user', 'content': 'hi'}]))

    # Patch the module's RateLimitError symbol to our dummy so the except block matches
    monkeypatch.setattr(chat_mod, 'RateLimitError', DummyRateLimitError)

    fake_client = FakeClient(to_raise=DummyRateLimitError('too many requests'))
    monkeypatch.setattr(ChatCerebras, '_client', lambda self: fake_client)

    model = ChatCerebras()

    # Act & Assert
    with pytest.raises(ModelRateLimitError) as excinfo:
        await model.ainvoke(messages=[SimpleNamespace()], output_format=None)
    assert 'too many requests' in str(excinfo.value)
    # Model name should be present in exception
    assert model.name in str(excinfo.value)


@pytest.mark.asyncio
async def test_json_output_extracts_and_parses_json_even_with_surrounding_text_and_appends_prompt_round_029(monkeypatch):
    """JSON path: appends prompt to last user message or adds a new one, extracts JSON via regex, and validates it."""
    # Arrange
    captured_messages_arg = None

    # Serializer returns a single user message (so branch that appends to last user message executes)
    cerebras_list = [{'role': 'user', 'content': 'original user content'}]
    monkeypatch.setattr(chat_mod, 'CerebrasMessageSerializer', SimpleNamespace(serialize_messages=lambda msgs: cerebras_list))

    # Create an output_format-like type with required methods
    class FakeOutputFormat:
        @staticmethod
        def model_json_schema():
            return {'type': 'object', 'properties': {'key': {'type': 'string'}}}

        @staticmethod
        def model_validate_json(s):
            # Return a deterministic parsed object for assertions
            # This also ensures the JSON string was extracted (it must contain {"key": "value"})
            if '{"key":"value"}' in s.replace(' ', '') or '{"key": "value"}' in s:
                return {'key': 'value'}
            # If not JSON-looking input, return an indicator
            return {'raw': s}

    # Response content contains surrounding text with embedded JSON; regex branch should find it
    resp = _FakeResponse('some preamble {"key":"value"} trailing text', usage=_FakeUsage())

    fake_client = FakeClient(to_return=resp)
    monkeypatch.setattr(ChatCerebras, '_client', lambda self: fake_client)

    model = ChatCerebras()
    # Set additional generation parameters to follow different branches (top_p and seed handled)
    model.top_p = 0.5
    model.seed = 42

    # Act
    result = await model.ainvoke(messages=[SimpleNamespace()], output_format=FakeOutputFormat)

    # Assert
    assert result.usage is not None
    assert result.completion == {'key': 'value'}

    # Check that the messages passed to the client had the json prompt appended to the original user message
    sent_messages = fake_client.last_call_args['kwargs']['messages']
    assert sent_messages is not None
    assert isinstance(sent_messages, list)
    # The last user message content should now include the JSON prompt instruction text (a substring)
    last_content = sent_messages[-1]['content']
    assert 'Please respond with a JSON object' in last_content or 'Your response must be valid JSON only' in last_content


@pytest.mark.asyncio
async def test_json_output_empty_content_raises_ModelProviderError_round_029(monkeypatch):
    """When the response has empty content on JSON path, a ModelProviderError is raised."""
    # Arrange
    monkeypatch.setattr(chat_mod, 'CerebrasMessageSerializer', SimpleNamespace(serialize_messages=lambda msgs: [{'role': 'user', 'content': 'ask json'}]))

    resp = _FakeResponse('', usage=_FakeUsage())
    fake_client = FakeClient(to_return=resp)
    monkeypatch.setattr(ChatCerebras, '_client', lambda self: fake_client)

    class FakeOutputFormat:
        @staticmethod
        def model_json_schema():
            return {'type': 'object'}

        @staticmethod
        def model_validate_json(s):
            return {}

    model = ChatCerebras()

    # Act & Assert
    with pytest.raises(ModelProviderError) as excinfo:
        await model.ainvoke(messages=[SimpleNamespace()], output_format=FakeOutputFormat)
    assert 'Empty JSON content' in str(excinfo.value)
