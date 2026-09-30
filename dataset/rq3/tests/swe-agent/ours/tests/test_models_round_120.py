import types
from sweagent.agent.models import LiteLLMModel


def test_query_with_n_none_round_120():
    # Create instance without running __init__ and patch _single_query
    inst = object.__new__(LiteLLMModel)
    seen = {}

    def fake_single_query(messages, temperature=None):
        # record the exact args to ensure temperature is forwarded
        seen['messages'] = messages
        seen['temperature'] = temperature
        return [{'response': f"{messages[0]['content']}-t{temperature}"}]

    # Attach the fake single-query implementation to the instance
    inst._single_query = types.MethodType(lambda self, messages, temperature=None: fake_single_query(messages, temperature), inst)

    messages = [{'role': 'user', 'content': 'hello'}]
    # Call _query with n=None to exercise the branch that delegates to a single query
    result = LiteLLMModel._query(inst, messages, n=None, temperature=0.5)

    # Oracle: should return the single-query result and preserve forwarded temperature/messages
    assert result == [{'response': 'hello-t0.5'}]
    assert seen['messages'] is messages
    assert seen['temperature'] == 0.5


def test_query_with_n_integer_extends_round_120():
    # Create instance without running __init__ and patch _single_query to be stateful
    inst = object.__new__(LiteLLMModel)
    call_counter = {'count': 0}

    def fake_single_query(messages, temperature=None):
        call_counter['count'] += 1
        # return a one-item list each call so extend behavior is observable
        return [{'call_index': call_counter['count']}]

    inst._single_query = types.MethodType(lambda self, messages, temperature=None: fake_single_query(messages, temperature), inst)

    messages = [{'role': 'user', 'content': 'x'}]
    # Call _query with an integer n to exercise the loop and extend path
    result = LiteLLMModel._query(inst, messages, n=3)

    # Oracle: result should contain three entries produced by three _single_query calls
    assert result == [{'call_index': 1}, {'call_index': 2}, {'call_index': 3}]
    assert call_counter['count'] == 3
