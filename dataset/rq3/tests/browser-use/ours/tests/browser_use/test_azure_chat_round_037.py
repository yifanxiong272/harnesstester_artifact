import pytest
import types
from types import SimpleNamespace

import browser_use.llm.azure.chat as chat_mod
from browser_use.llm.azure.chat import ChatAzureOpenAI

# Helper stubs
class StubResponse:
    def __init__(self, output_text=None, status=None):
        self.output_text = output_text
        self.status = status

class ClientStub:
    def __init__(self, create_coro):
        # The code under test expects client.responses.create(...)
        self.responses = SimpleNamespace(create=create_coro)


def _valid_usage(completion_tokens: int = 0):
    # Provide all required usage fields expected by ChatInvokeUsage validation
    return {
        'prompt_tokens': 0,
        'prompt_cached_tokens': 0,
        'prompt_cache_creation_tokens': 0,
        'prompt_image_tokens': 0,
        'completion_tokens': completion_tokens,
        'total_tokens': completion_tokens,
    }


@pytest.mark.asyncio
async def test_string_response_includes_temperature_round_037(monkeypatch):
    """
    Covers: serialization -> model_params building including temperature, top_p, max_output_tokens, service_tier
    and string-output return path (output_format is None).
    """
    recorded_kwargs = {}

    async def fake_create(**kwargs):
        # capture provided kwargs for assertion
        recorded_kwargs.update(kwargs)
        return StubResponse(output_text='hello world', status='done')

    # Ensure serialization returns something predictable
    monkeypatch.setattr(
        chat_mod.ResponsesAPIMessageSerializer,
        'serialize_messages',
        lambda msgs: [{'role': 'user', 'content': 'hi'}],
    )

    # Build instance with several optional params set
    inst = ChatAzureOpenAI(
        model='gpt-test',
        api_key='k',
        temperature=0.7,
        max_completion_tokens=123,
        top_p=0.9,
        service_tier='premium',
    )

    # Attach client stub directly so get_client returns it
    inst.client = ClientStub(create_coro=fake_create)

    # Patch usage extractor to a deterministic and valid value
    monkeypatch.setattr(inst, '_get_usage_from_responses', lambda resp: _valid_usage(completion_tokens=5))

    result = await inst._ainvoke_responses_api(messages=[SimpleNamespace()], output_format=None)

    # Observables
    assert hasattr(result, 'completion') and result.completion == 'hello world'
    assert hasattr(result, 'stop_reason') and result.stop_reason == 'done'
    # Model params passed into create must include the serialized input and our optional params
    assert recorded_kwargs['input'] == [{'role': 'user', 'content': 'hi'}]
    assert recorded_kwargs['temperature'] == 0.7
    assert recorded_kwargs['max_output_tokens'] == 123
    assert recorded_kwargs['top_p'] == 0.9
    assert recorded_kwargs['service_tier'] == 'premium'


@pytest.mark.asyncio
async def test_structured_output_reasoning_schema_list_content_round_037(monkeypatch):
    """
    Covers: structured-output branch, reasoning_models effect (reasoning replaces temperature),
    SchemaOptimizer usage, adding JSON schema to a system message whose content is a list,
    dont_force_structured_output path (pop of 'text'). Also covers parsing via output_format.model_validate_json.
    """
    recorded_kwargs = {}

    async def fake_create(**kwargs):
        recorded_kwargs.update(kwargs)
        # Return non-empty output_text to allow parsing path
        return StubResponse(output_text='{"x": 1}', status=None)

    # Serialized messages: first message is system and content is a list (to hit the list branch)
    monkeypatch.setattr(
        chat_mod.ResponsesAPIMessageSerializer,
        'serialize_messages',
        lambda msgs: [
            {'role': 'system', 'content': [{'type': 'input_text', 'text': 'original'}]},
            {'role': 'user', 'content': 'ask'}
        ],
    )

    # Schema optimizer returns predictable schema string
    monkeypatch.setattr(
        chat_mod.SchemaOptimizer,
        'create_optimized_json_schema',
        lambda output_format, remove_min_items, remove_defaults: '{"type":"object","properties":{"x":{"type":"integer"}}}',
    )

    # Dummy output_format with model_validate_json
    class DummyOutputFormat:
        @staticmethod
        def model_validate_json(text):
            # Expect the Response.output_text to be JSON string
            assert text.strip().startswith('{')
            return {'parsed': True}

    inst = ChatAzureOpenAI(
        model='reasoner-model',
        api_key='k',
        temperature=0.9,  # should be removed due to reasoning_models match
        reasoning_models=['reasoner'],
        reasoning_effort=5,
        add_schema_to_system_prompt=True,
        remove_min_items_from_schema=False,
        remove_defaults_from_schema=False,
        dont_force_structured_output=True,  # should remove the 'text' key before create
    )

    inst.client = ClientStub(create_coro=fake_create)
    # Provide a complete usage mapping to satisfy ChatInvokeCompletion validation
    monkeypatch.setattr(inst, '_get_usage_from_responses', lambda resp: _valid_usage(completion_tokens=1))

    result = await inst._ainvoke_responses_api(messages=[SimpleNamespace()], output_format=DummyOutputFormat)

    # Check that reasoning parameter was set and temperature removed
    assert 'reasoning' in recorded_kwargs and recorded_kwargs['reasoning'] == {'effort': 5}
    assert 'temperature' not in recorded_kwargs

    # Because add_schema_to_system_prompt was true and the first message content was a list,
    # the input should have been replaced with a list containing the schema text chunk as an input_text element
    assert isinstance(recorded_kwargs['input'][0]['content'], list)
    # The text format should have been removed due to dont_force_structured_output
    assert 'text' not in recorded_kwargs

    # Parsed completion should be the object returned by model_validate_json
    assert hasattr(result, 'completion') and result.completion == {'parsed': True}
    assert result.stop_reason is None


@pytest.mark.asyncio
async def test_rate_limit_and_api_status_translated_round_037(monkeypatch):
    """
    Covers: exception translation branches for RateLimitError -> ModelRateLimitError and APIStatusError -> ModelProviderError.
    """
    # Create custom exception classes to avoid dependency on openai lib and to control attributes
    class MyRateLimitError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    class MyAPIStatusError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    # Patch the module-level exception symbols the code under test catches
    monkeypatch.setattr(chat_mod, 'RateLimitError', MyRateLimitError)
    monkeypatch.setattr(chat_mod, 'APIStatusError', MyAPIStatusError)

    # Case 1: RateLimitError should raise ModelRateLimitError
    async def create_raises_rate(**kwargs):
        raise MyRateLimitError('too many requests')

    inst1 = ChatAzureOpenAI(model='m')
    inst1.client = ClientStub(create_coro=create_raises_rate)

    with pytest.raises(chat_mod.ModelRateLimitError) as ei:
        await inst1._ainvoke_responses_api(messages=[SimpleNamespace()], output_format=None)
    # Ensure message propagated
    assert 'too many requests' in str(ei.value)

    # Case 2: APIStatusError should be translated to ModelProviderError with status_code
    async def create_raises_status(**kwargs):
        raise MyAPIStatusError('bad status', 502)

    inst2 = ChatAzureOpenAI(model='m')
    inst2.client = ClientStub(create_coro=create_raises_status)

    with pytest.raises(chat_mod.ModelProviderError) as esi:
        await inst2._ainvoke_responses_api(messages=[SimpleNamespace()], output_format=None)
    # Ensure status message propagated
    assert 'bad status' in str(esi.value)
