import types
from types import SimpleNamespace
import pytest
import sweagent.agent.models as models

# Helper to build a minimal LiteLLMModel instance without calling __init__
def make_instance():
    inst = object.__new__(models.LiteLLMModel)
    # no-op helpers expected by _single_query
    inst._sleep = lambda: None
    inst._update_stats = lambda **kwargs: None
    inst.logger = SimpleNamespace(
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        debug=lambda *a, **k: None,
        error=lambda *a, **k: None,
    )
    return inst


def test_success_with_tool_calls_round_005(monkeypatch):
    # Ensure cache_control keys are removed before token counting and that
    # anthropic branch sets max_tokens; also ensure tool_calls are preserved.

    # token_counter should receive messages without cache_control and later be
    # called for text token counting. Distinguish by kwargs.
    def token_counter(**kwargs):
        if 'messages' in kwargs:
            # assert cache_control removed
            for m in kwargs['messages']:
                assert 'cache_control' not in m
            return 1
        if 'text' in kwargs:
            # deterministic token count for the output
            return len(kwargs['text'])
        return 0

    # completion returns a response-like object expected by _single_query
    def completion(**kwargs):
        # emulate litellm response structure: response.choices[i].message.content and .message.tool_calls
        tool_call_obj = SimpleNamespace(to_dict=lambda: {'tool': 'call', 'args': [1]})
        message = SimpleNamespace(content='hi', tool_calls=[tool_call_obj])
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])

    cost_calc = SimpleNamespace(completion_cost=lambda resp: 0.2)

    fake_litellm = SimpleNamespace(
        utils=SimpleNamespace(token_counter=token_counter),
        completion=completion,
        cost_calculator=cost_calc,
        exceptions=SimpleNamespace(
            BadRequestError=Exception,
            ContextWindowExceededError=Exception,
            ContentPolicyViolationError=Exception,
        ),
        types=SimpleNamespace(utils=SimpleNamespace()),
    )

    monkeypatch.setattr(models, 'litellm', fake_litellm)

    inst = make_instance()
    # minimal config and tools matching the shape used in _single_query
    inst.config = SimpleNamespace(
        name='test-model',
        temperature=0.5,
        top_p=1.0,
        api_version='v1',
        choose_api_key=lambda: 'dummy',
        fallbacks=None,
        completion_kwargs={},
        api_base=None,
        per_instance_cost_limit=0,
        total_cost_limit=0,
    )
    inst.tools = SimpleNamespace(use_function_calling=True, tools=[{'tool': 'x'}])
    inst.model_max_input_tokens = 100
    inst.model_max_output_tokens = 5
    inst.lm_provider = 'anthropic'

    messages = [{'role': 'user', 'content': 'hello', 'cache_control': 'no-cache'}]

    outputs = inst._single_query(messages)

    assert outputs == [{
        'message': 'hi',
        'tool_calls': [{'tool': 'call', 'args': [1]}]
    }]
    # anthropic branch should have set max_tokens in completion_kwargs
    assert inst.config.completion_kwargs.get('max_tokens') == inst.model_max_output_tokens


def test_badrequest_context_window_round_005(monkeypatch):
    # If litellm.completion raises a BadRequestError mentioning context length,
    # _single_query should raise our ContextWindowExceededError.

    class FakeBadRequestError(Exception):
        pass

    def token_counter(**kwargs):
        # simple deterministic token counts
        return 1

    def completion(**kwargs):
        # raise BadRequestError with the message fragment checked in the code
        raise FakeBadRequestError("input is longer than the model's context length")

    fake_litellm = SimpleNamespace(
        utils=SimpleNamespace(token_counter=token_counter),
        completion=completion,
        cost_calculator=SimpleNamespace(completion_cost=lambda resp: 0),
        exceptions=SimpleNamespace(
            BadRequestError=FakeBadRequestError,
            ContextWindowExceededError=FakeBadRequestError,
            ContentPolicyViolationError=Exception,
        ),
        types=SimpleNamespace(utils=SimpleNamespace()),
    )

    monkeypatch.setattr(models, 'litellm', fake_litellm)

    inst = make_instance()
    inst.config = SimpleNamespace(
        name='m',
        temperature=0.0,
        top_p=1.0,
        api_version='v1',
        choose_api_key=lambda: None,
        fallbacks=None,
        completion_kwargs={},
        api_base=None,
        per_instance_cost_limit=0,
        total_cost_limit=0,
    )
    inst.tools = SimpleNamespace(use_function_calling=False, tools=[])
    inst.model_max_input_tokens = 10
    inst.model_max_output_tokens = 5
    inst.lm_provider = 'openai'

    with pytest.raises(models.ContextWindowExceededError):
        inst._single_query([{'role': 'user', 'content': 'hello'}])


def test_cost_calc_failure_raises_model_config_error_round_005(monkeypatch):
    # If cost calculation raises and cost limits are > 0, a ModelConfigurationError is raised.

    def token_counter(**kwargs):
        return 1

    def completion(**kwargs):
        message = SimpleNamespace(content='ok', tool_calls=None)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])

    def broken_completion_cost(resp):
        raise Exception('boom')

    fake_litellm = SimpleNamespace(
        utils=SimpleNamespace(token_counter=token_counter),
        completion=completion,
        cost_calculator=SimpleNamespace(completion_cost=broken_completion_cost),
        exceptions=SimpleNamespace(
            BadRequestError=Exception,
            ContextWindowExceededError=Exception,
            ContentPolicyViolationError=Exception,
        ),
        types=SimpleNamespace(utils=SimpleNamespace()),
    )

    monkeypatch.setattr(models, 'litellm', fake_litellm)

    inst = make_instance()
    inst.config = SimpleNamespace(
        name='m',
        temperature=0.0,
        top_p=1.0,
        api_version='v1',
        choose_api_key=lambda: None,
        fallbacks=None,
        completion_kwargs={},
        api_base=None,
        per_instance_cost_limit=1,  # triggers error path when cost calc fails
        total_cost_limit=0,
    )
    inst.tools = SimpleNamespace(use_function_calling=False, tools=[])
    inst.model_max_input_tokens = 100
    inst.model_max_output_tokens = 10
    inst.lm_provider = 'openai'

    with pytest.raises(models.ModelConfigurationError):
        inst._single_query([{'role': 'user', 'content': 'hello'}])
