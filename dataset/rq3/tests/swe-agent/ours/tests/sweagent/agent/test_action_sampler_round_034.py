import pytest
from types import SimpleNamespace
from sweagent.agent.action_sampler import BinaryTrajectoryComparison, ActionSamplerOutput


def test_get_action_two_completions_round_034():
    inst = BinaryTrajectoryComparison.__new__(BinaryTrajectoryComparison)

    # completions must be dicts to satisfy ActionSamplerOutput.completion pydantic type
    completions = [{"id": 0, "text": "completion_0"}, {"id": 1, "text": "completion_1"}]
    inst.get_completions = lambda history: completions

    # parse_actions should accept the completion dict
    inst._tools = SimpleNamespace(parse_actions=lambda c: (f"thought_of_{c['id']}", f"action_of_{c['id']}"))

    inst.format_messages = lambda **kwargs: [{"role": "system", "content": "msg"}]

    # model.query returns dict with a "message" key; interpret maps to chosen index
    inst._model = SimpleNamespace(query=lambda messages, temperature: {"message": "CHOICE: 1"})
    inst.interpret = lambda response: 1
    inst.config = SimpleNamespace(comparison_temperature=0.0)
    inst._logger = SimpleNamespace(info=lambda *a, **k: None)

    out = inst.get_action(problem_statement=None, trajectory=None, history=[])

    assert isinstance(out, ActionSamplerOutput)
    # completion should be the dict object from completions[1]
    assert out.completion == completions[1]
    comparison_log = out.extra_info.get("comparison_log")
    assert isinstance(comparison_log, list) and len(comparison_log) == 1
    entry = comparison_log[0]
    assert entry["comparison_between"] == (0, 1)
    assert entry["idx"] == 1
    assert entry["response"] == "CHOICE: 1"


def test_get_action_single_completion_skips_loop_round_034():
    inst = BinaryTrajectoryComparison.__new__(BinaryTrajectoryComparison)

    completions = [{"id": 0, "text": "only_completion"}]
    inst.get_completions = lambda history: completions

    inst._tools = SimpleNamespace(parse_actions=lambda c: ("t", "a"))

    # If model.query is called unexpectedly, fail the test
    def fail_query(*_a, **_k):
        pytest.fail("model.query should not be called when there is only one completion")

    inst._model = SimpleNamespace(query=fail_query)
    inst.format_messages = lambda **kwargs: []
    inst.interpret = lambda response: 0
    inst.config = SimpleNamespace(comparison_temperature=0.0)
    inst._logger = SimpleNamespace(info=lambda *a, **k: None)

    out = inst.get_action(problem_statement=None, trajectory=None, history=[])

    assert isinstance(out, ActionSamplerOutput)
    assert out.completion == completions[0]
    assert out.extra_info.get("comparison_log") == []


def test_get_action_three_completions_use_cache_round_034():
    inst = BinaryTrajectoryComparison.__new__(BinaryTrajectoryComparison)

    completions = [
        {"id": 0, "text": "c0"},
        {"id": 1, "text": "c1"},
        {"id": 2, "text": "c2"},
    ]
    inst.get_completions = lambda history: completions

    inst._tools = SimpleNamespace(parse_actions=lambda c: (f"thought_{c['id']}", f"action_{c['id']}"))

    format_calls = []

    def record_format_messages(**kwargs):
        format_calls.append(kwargs)
        return [{"role": "system", "content": "compare"}]

    inst.format_messages = record_format_messages

    # Two comparisons expected: i=1 then i=2
    responses = ["m0", "m1"]

    def fake_query(messages, temperature):
        return {"message": responses.pop(0)}

    inst._model = SimpleNamespace(query=fake_query)

    def interpret_map(response):
        return 0 if response == "m0" else 1

    inst.interpret = interpret_map
    inst.config = SimpleNamespace(comparison_temperature=0.1)
    inst._logger = SimpleNamespace(info=lambda *a, **k: None)

    out = inst.get_action(problem_statement=None, trajectory=None, history=[])

    # final best index should be 2 because second comparison returned idx=1
    assert out.completion == completions[2]

    log = out.extra_info.get("comparison_log")
    assert isinstance(log, list) and len(log) == 2
    assert log[0]["idx"] == 0
    assert log[1]["idx"] == 1

    # format_messages should have been called and use_cache_control must be True
    assert format_calls, "format_messages was not called"
    for call_kwargs in format_calls:
        assert call_kwargs.get("use_cache_control") is True
