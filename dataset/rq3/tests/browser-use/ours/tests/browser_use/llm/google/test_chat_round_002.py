import asyncio
import json
import types as pytypes
from types import SimpleNamespace
import importlib
import pytest

chat_mod = importlib.import_module('browser_use.llm.google.chat')

# Lightweight replacements to avoid importing real SDK types
class SimpleCompletion:
    def __init__(self, completion, usage=None, stop_reason=None):
        self.completion = completion
        self.usage = usage
        self.stop_reason = stop_reason


@pytest.mark.asyncio
async def test_text_response_empty_is_handled_round_002(monkeypatch):
    """Test that text responses where response.text is None are handled and return empty completion."""
    # Patch ChatInvokeCompletion to a simple container so construction inside ainvoke succeeds
    monkeypatch.setattr(chat_mod, 'ChatInvokeCompletion', SimpleCompletion)

    # Patch serializer to return simple contents and no system instruction
    monkeypatch.setattr(chat_mod.GoogleMessageSerializer, 'serialize_messages', staticmethod(lambda messages, include_system_in_user: (['c'], None)))

    # Minimal types replacements used by ainvoke
    monkeypatch.setattr(chat_mod.types, 'ThinkingLevel', lambda x: x)
    monkeypatch.setattr(chat_mod.types, 'ThinkingConfigDict', lambda **kwargs: kwargs)

    # Create a fake response with no text to hit the empty-text warning branch
    response = SimpleNamespace()
    response.text = None
    response.parsed = None

    # Fake client that returns our response
    class FakeModels:
        def __init__(self, resp):
            self._resp = resp

        async def generate_content(self, model, contents, config):
            return self._resp

    class FakeAio:
        def __init__(self, resp):
            self.models = FakeModels(resp)

    class FakeClient:
        def __init__(self, resp):
            self.aio = FakeAio(resp)

    # Fake self to pass into the unbound method; set attributes to follow the gemini-2.5 branch
    class FakeSelf:
        include_system_in_user = False
        config = {'user': 'val'}
        temperature = None
        model = 'gemini-2.5'
        top_p = None
        seed = None
        thinking_level = None
        thinking_budget = None
        max_output_tokens = None
        supports_structured_output = False
        max_retries = 1
        retryable_status_codes = []
        retry_base_delay = 0.1
        retry_max_delay = 1
        name = 'fake-chat'

        def __init__(self, resp):
            self._client = FakeClient(resp)
            # simple logger with required methods
            class L:
                def debug(self, *_):
                    pass

                def warning(self, *_):
                    pass

                def error(self, *_):
                    pass

            self.logger = L()

        def get_client(self):
            return self._client

        def _get_usage(self, resp):
            return {'tokens': 0}

        def _get_stop_reason(self, resp):
            return 'stop'

    fake_self = FakeSelf(response)

    # call the unbound async function with fake_self
    result = await chat_mod.ChatGoogle.ainvoke(fake_self, messages=[], output_format=None)

    # Assert the returned completion is the empty string (text was None -> '' expected)
    assert isinstance(result, SimpleCompletion)
    assert result.completion == ''


@pytest.mark.asyncio
async def test_structured_output_json_wrapped_in_markdown_round_002(monkeypatch):
    """Test structured output path where Gemini returns JSON wrapped in ```json code fences.

    This covers the branch that strips ```json``` wrappers, parses the JSON, and validates
    using the output_format.model_validate call.
    """
    # Patch ChatInvokeCompletion to a simple container
    monkeypatch.setattr(chat_mod, 'ChatInvokeCompletion', SimpleCompletion)

    # Ensure serializer returns a placeholder contents tuple
    monkeypatch.setattr(chat_mod.GoogleMessageSerializer, 'serialize_messages', staticmethod(lambda messages, include_system_in_user: (['c'], None)))

    # Patch SchemaOptimizer and any schema fixer used in ainvoke to avoid heavy logic
    monkeypatch.setattr(chat_mod.SchemaOptimizer, 'create_gemini_optimized_schema', staticmethod(lambda out: {'schema': 'opt'}))

    # Replace module-level types helpers used by the code
    monkeypatch.setattr(chat_mod.types, 'ThinkingLevel', lambda x: x)
    monkeypatch.setattr(chat_mod.types, 'ThinkingConfigDict', lambda **kwargs: kwargs)

    # Provide an output format with model_validate to be called with parsed JSON
    class FakeOutModel:
        __name__ = 'FakeOutModel'

        @classmethod
        def model_validate(cls, data):
            # Return a clear sentinel showing validation was invoked
            return {'validated': True, 'data': data}

    # Fake response: parsed is None, but text contains ```json wrapper
    json_payload = {'hello': 'world', 'num': 123}
    raw_text = '```json\n' + json.dumps(json_payload) + '\n```'
    response = SimpleNamespace()
    response.text = raw_text
    response.parsed = None

    # Fake client that returns our response when generate_content is awaited
    class FakeModels:
        def __init__(self, resp):
            self._resp = resp

        async def generate_content(self, model, contents, config):
            return self._resp

    class FakeAio:
        def __init__(self, resp):
            self.models = FakeModels(resp)

    class FakeClient:
        def __init__(self, resp):
            self.aio = FakeAio(resp)

    # Fake self to exercise the gemini-3-flash branch where thinking_budget gets defaulted
    class FakeSelf:
        include_system_in_user = False
        config = None
        temperature = 0.7
        model = 'gemini-3-flash'
        top_p = None
        seed = None
        thinking_level = None
        thinking_budget = None
        max_output_tokens = None
        supports_structured_output = True
        max_retries = 1
        retryable_status_codes = []
        retry_base_delay = 0.1
        retry_max_delay = 1
        name = 'fake-chat'

        def __init__(self, resp):
            self._client = FakeClient(resp)
            class L:
                def debug(self, *_):
                    pass

                def warning(self, *_):
                    pass

                def error(self, *_):
                    pass

            self.logger = L()

        def get_client(self):
            return self._client

        def _get_usage(self, resp):
            return {'tokens': 5}

        def _get_stop_reason(self, resp):
            return 'stop'

        # _fix_gemini_schema is called in ainvoke; provide a noop pass-through
        def _fix_gemini_schema(self, optimized_schema):
            return optimized_schema

    fake_self = FakeSelf(response)

    # Call the method: expect the JSON within code fences to be parsed and validated
    result = await chat_mod.ChatGoogle.ainvoke(fake_self, messages=[], output_format=FakeOutModel)

    assert isinstance(result, SimpleCompletion)
    # The completion should be the value returned by FakeOutModel.model_validate
    assert result.completion == {'validated': True, 'data': json_payload}
