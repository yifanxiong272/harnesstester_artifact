import asyncio
import types
from types import SimpleNamespace
from typing import List

import httpx

import browser_use.llm.browser_use.chat as chat_mod

# Tests exercise ChatBrowserUse.ainvoke behavior deterministically without network

class FakeActionModel:
    def __init__(self, data):
        self.data = data

    @classmethod
    def model_validate(cls, action_dict):
        # Return a simple object so tests can observe conversion
        return cls(action_dict)


class FakeOutputFormat:
    # Provide the minimal API used by ainvoke: model_json_schema, model_fields, model_validate
    model_fields = {'action': SimpleNamespace(annotation=List[FakeActionModel])}

    @classmethod
    def model_json_schema(cls):
        return {'fake': 'schema'}

    @classmethod
    def model_validate(cls, data):
        # Return a tangible sentinel so the test can assert on completion
        data['_validated'] = True
        return data


class DummyUsage:
    def __init__(self, **kwargs):
        self._data = kwargs


def make_instance():
    # Construct a ChatBrowserUse instance without invoking real network or complex init
    inst = object.__new__(chat_mod.ChatBrowserUse)
    # Set required attributes referenced by ainvoke
    inst.model = 'fake-model'
    inst.fast = False
    inst.max_retries = 3
    inst.retry_base_delay = 0.01
    inst.retry_max_delay = 0.02
    inst.timeout = 1.23

    # Provide a trivial serializer used for messages
    def _serialize_message(self, msg):
        return {'role': getattr(msg, 'role', 'user'), 'content': getattr(msg, 'content', str(msg))}

    inst._serialize_message = types.MethodType(_serialize_message, inst)
    return inst


async def _nop_sleep(_):
    # Avoid real sleeping in tests
    return None


def setup_module(module):
    # Replace ChatInvokeUsage used inside ainvoke with DummyUsage so imports inside function resolve
    # The function imports from browser_use.llm.views inside the function body; patch the module object
    import browser_use.llm.views as v_mod

    v_mod.ChatInvokeUsage = DummyUsage

    # Ensure deterministic jitter
    chat_mod.random.uniform = lambda a, b: 0.0

    # Patch asyncio.sleep used in retry logic
    chat_mod.asyncio.sleep = _nop_sleep

    # Ensure predictable telemetry setting
    import browser_use.config as cfg

    cfg.CONFIG = SimpleNamespace(ANONYMIZED_TELEMETRY=False)


def test_structured_action_conversion_round_097():
    """
    Verify that when a structured completion with action dicts is returned,
    ainvoke converts action dicts to model instances and validates the final output_format.
    This also covers adding session_id and output_format schema to the outgoing payload.
    """
    inst = make_instance()

    # Prepare a sentinel result the fake _make_request will return
    result = {
        'completion': {
            'action': [{'type': 'click', 'target': 'button-1'}],
            'other': 'value'
        },
        'usage': {'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3}
    }

    async def fake_make_request(self, payload):
        # Assert payload contains session_id and the serialized output_format schema
        assert payload['session_id'] == 'sess-42'
        assert payload['output_format'] == FakeOutputFormat.model_json_schema()
        # Ensure telemetry and model fields are present
        assert payload['anonymized_telemetry'] is False
        assert payload['model'] == inst.model
        return result

    inst._make_request = types.MethodType(fake_make_request, inst)

    # Call ainvoke and verify the returned ChatInvokeCompletion contains validated completion and usage
    async def runner():
        completion_obj = await chat_mod.ChatBrowserUse.ainvoke(inst, messages=[SimpleNamespace(role='user', content='hi')], output_format=FakeOutputFormat, session_id='sess-42')
        # The output_format.model_validate sets '_validated' key
        assert completion_obj.completion.get('_validated', False) is True
        # After conversion, 'action' elements should be instances of FakeActionModel
        actions = completion_obj.completion['action']
        assert isinstance(actions, list) and isinstance(actions[0], FakeActionModel)
        # Usage should be instance of DummyUsage created inside function
        assert isinstance(completion_obj.usage, DummyUsage)

    asyncio.run(runner())


def test_timeout_raises_value_error_round_097():
    """
    When _make_request raises httpx.TimeoutException and retries are exhausted immediately (max_retries=1),
    ainvoke raises a ValueError with a timeout message.
    """
    inst = make_instance()
    inst.max_retries = 1

    async def raise_timeout(self, payload):
        raise httpx.TimeoutException('simulated timeout')

    inst._make_request = types.MethodType(raise_timeout, inst)

    async def runner():
        try:
            await chat_mod.ChatBrowserUse.ainvoke(inst, messages=["m"], output_format=None)
            raise AssertionError('Expected ValueError not raised')
        except ValueError as e:
            # Ensure error message mentions timeout and number of retries
            assert 'timed out' in str(e)
            assert str(inst.timeout) in str(e)
            assert str(inst.max_retries) in str(e)

    asyncio.run(runner())


def test_httpstatus_non_retry_calls_raise_round_097():
    """
    When _make_request raises an HTTPStatusError with a non-retryable status code,
    ainvoke should delegate to _raise_http_error; we patch _raise_http_error to raise a sentinel.
    """
    inst = make_instance()
    inst.max_retries = 3

    # Create a fake response with a 400 status (non-retryable)
    fake_response = SimpleNamespace(status_code=400)

    async def raise_http_error_exc(self, payload):
        raise httpx.HTTPStatusError('bad', request=None, response=fake_response)

    inst._make_request = types.MethodType(raise_http_error_exc, inst)

    # Patch _raise_http_error to raise a specific exception we can assert on
    def raise_from_raise_http_error(self, e):
        raise RuntimeError('raised from _raise_http_error')

    inst._raise_http_error = types.MethodType(raise_from_raise_http_error, inst)

    async def runner():
        try:
            await chat_mod.ChatBrowserUse.ainvoke(inst, messages=["m"], output_format=None)
            raise AssertionError('Expected RuntimeError not raised')
        except RuntimeError as e:
            assert 'raised from _raise_http_error' in str(e)

    asyncio.run(runner())


def test_zero_max_retries_raises_runtimeerror_round_097():
    """
    When max_retries is set to 0 the retry loop body is never entered; the for-else branch
    should hit the final RuntimeError('Retry loop completed without return or exception').
    This exercises the for-else path in ainvoke.
    """
    inst = make_instance()
    inst.max_retries = 0

    async def runner():
        try:
            await chat_mod.ChatBrowserUse.ainvoke(inst, messages=["m"], output_format=None)
            raise AssertionError('Expected RuntimeError not raised')
        except RuntimeError as e:
            assert 'Retry loop completed without return or exception' in str(e)

    asyncio.run(runner())
