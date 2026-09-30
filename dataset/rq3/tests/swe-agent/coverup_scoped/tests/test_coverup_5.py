# file: sweagent/agent/action_sampler.py:266-304
# asked: {"lines": [273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 288, 289, 290, 291, 292, 293, 294, 295, 296, 299, 301, 302, 303], "branches": [[276, 277], [276, 301]]}
# gained: {"lines": [273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 288, 289, 290, 291, 292, 293, 294, 295, 296, 299, 301, 302, 303], "branches": [[276, 277], [276, 301]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyModel:
    def __init__(self):
        self.calls = []

    def query(self, messages, temperature=None):
        # record the call
        self.calls.append({"messages": messages, "temperature": temperature})
        # Return a placeholder message string that the real code expects under key "message"
        return {"message": "DUMMY_RESPONSE"}


class DummyTools:
    def __init__(self):
        self.parse_calls = []

    def parse_actions(self, completion):
        # record and return a thought/action based on completion content
        self.parse_calls.append(completion)
        return (f"thought_{completion['id']}", f"action_{completion['id']}")


def make_instance(config_temp=0.5):
    config = SimpleNamespace(comparison_temperature=config_temp)
    model = DummyModel()
    tools = DummyTools()
    return BinaryTrajectoryComparison(config=config, model=model, tools=tools)


def test_get_action_with_two_completions_updates_best_idx_and_logs(monkeypatch):
    instance = make_instance(config_temp=0.25)

    # Prepare completions: two items to trigger one comparison (range(1,2))
    completions = [{"id": 0, "text": "c0"}, {"id": 1, "text": "c1"}]

    # Monkeypatch get_completions to return our completions
    monkeypatch.setattr(instance, "get_completions", lambda history: completions)

    # Capture the use_cache_control passed to format_messages
    captured = {}

    def fake_format_messages(*, problem_statement, trajectory, thought1, action1, thought2, action2, use_cache_control=False):
        # record values for assertions
        captured["use_cache_control"] = use_cache_control
        captured["thought1"] = thought1
        captured["action1"] = action1
        captured["thought2"] = thought2
        captured["action2"] = action2
        # Return a messages list that our model will receive
        return [{"role": "system", "content": f"compare {thought1} vs {thought2}"}]

    monkeypatch.setattr(instance, "format_messages", fake_format_messages)

    # Ensure interpret returns 1 so best_idx gets updated to i (1)
    monkeypatch.setattr(instance, "interpret", lambda response: 1)

    # Run get_action
    output = instance.get_action(problem_statement=SimpleNamespace(), trajectory=[], history=[])

    # Assertions
    assert captured["use_cache_control"] is False
    assert captured["thought1"] == "thought_0"
    assert captured["action1"] == "action_0"
    assert captured["thought2"] == "thought_1"
    assert captured["action2"] == "action_1"

    # The completion returned should equal completions[1] because interpret returned 1
    assert output.completion == completions[1]
    # comparison_log should contain one entry with expected structure
    comp_log = output.extra_info["comparison_log"]
    assert isinstance(comp_log, list)
    assert len(comp_log) == 1
    entry = comp_log[0]
    assert entry["comparison_between"] == (0, 1)
    assert entry["idx"] == 1
    assert entry["response"] == "DUMMY_RESPONSE"
    assert "messages" in entry
    assert entry["messages"][0]["content"] == "compare thought_0 vs thought_1"

    # Ensure the model was called with the temperature from config
    assert instance._model.calls[0]["temperature"] == instance.config.comparison_temperature


def test_get_action_with_three_completions_checks_cache_control_and_multiple_comparisons(monkeypatch):
    instance = make_instance(config_temp=0.75)

    # Prepare completions: three items to trigger two comparisons (i=1 and i=2)
    completions = [{"id": 0, "text": "c0"}, {"id": 1, "text": "c1"}, {"id": 2, "text": "c2"}]

    monkeypatch.setattr(instance, "get_completions", lambda history: completions)

    # We'll capture each format_messages call to assert use_cache_control=True
    calls = []

    def fake_format_messages(*, problem_statement, trajectory, thought1, action1, thought2, action2, use_cache_control=False):
        calls.append({
            "thought1": thought1,
            "action1": action1,
            "thought2": thought2,
            "action2": action2,
            "use_cache_control": use_cache_control,
        })
        return [{"role": "system", "content": f"compare {thought1} vs {thought2}"}]

    monkeypatch.setattr(instance, "format_messages", fake_format_messages)

    # Interpret should return 0 for the first comparison (keep best_idx=0) and 1 for the second (set best_idx=2)
    interpret_results = [0, 1]

    def fake_interpret(response):
        return interpret_results.pop(0)

    monkeypatch.setattr(instance, "interpret", fake_interpret)

    # Run get_action
    output = instance.get_action(problem_statement=SimpleNamespace(), trajectory=[], history=[])

    # Assertions: format_messages should have been called twice and use_cache_control True both times
    assert len(calls) == 2
    assert all(call["use_cache_control"] is True for call in calls)

    # Check that the thoughts/actions used match parse_actions for respective completion ids
    # First comparison was between (0,1)
    assert calls[0]["thought1"] == "thought_0"
    assert calls[0]["action1"] == "action_0"
    assert calls[0]["thought2"] == "thought_1"
    assert calls[0]["action2"] == "action_1"
    # Second comparison was between (0,2) because best_idx remained 0 after first comparison
    assert calls[1]["thought1"] == "thought_0"
    assert calls[1]["action1"] == "action_0"
    assert calls[1]["thought2"] == "thought_2"
    assert calls[1]["action2"] == "action_2"

    # The final chosen completion should equal completions[2] because interpret returned 1 on second comparison
    assert output.completion == completions[2]

    comp_log = output.extra_info["comparison_log"]
    assert len(comp_log) == 2
    # Check entries recorded the correct comparison_between tuples and idx values
    assert comp_log[0]["comparison_between"] == (0, 1)
    assert comp_log[0]["idx"] == 0
    assert comp_log[1]["comparison_between"] == (0, 2)
    assert comp_log[1]["idx"] == 1

    # Ensure the model was called twice and with the configured temperature
    assert len(instance._model.calls) == 2
    assert all(call["temperature"] == instance.config.comparison_temperature for call in instance._model.calls)
