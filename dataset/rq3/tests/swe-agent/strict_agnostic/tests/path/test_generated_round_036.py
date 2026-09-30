import pytest
from types import SimpleNamespace

from sweagent.agent.action_sampler import BinaryTrajectoryComparison, ActionSamplerOutput


class DummyModel:
    """Deterministic fake model that returns preset responses and records calls."""
    def __init__(self, responses):
        # copy to avoid mutation of caller lists
        self.responses = list(responses)
        self.calls = []

    def query(self, messages, temperature):
        # record call for assertions, return next preset response
        self.calls.append({"messages": messages, "temperature": temperature})
        if not self.responses:
            raise RuntimeError("No more responses configured in DummyModel")
        return {"message": self.responses.pop(0)}


class DummyTools:
    """Deterministic fake tools with a parse_actions implementation that accepts dict completions.

    The real code expects completions to be mapping-like objects (not plain strings), so
    tests must provide dict-like completions. This helper tolerates both dict and str for convenience.
    """
    def parse_actions(self, completion):
        # completion might be a dict such as {"content": "..."} or a plain string.
        if isinstance(completion, dict):
            content = completion.get("content") if "content" in completion else completion
        else:
            content = completion
        # return tuple (thought, action) derived from the content
        return (f"thought_of_{content}", f"action_of_{content}")


def _make_instance(model, tools, comparison_temperature=0.5):
    """Create BinaryTrajectoryComparison instance without invoking its real __init__
    and set up required attributes for get_action to run deterministically.
    """
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._model = model
    inst._tools = tools
    inst.config = SimpleNamespace(comparison_temperature=comparison_temperature)
    # lightweight logger that doesn't emit to real outputs
    inst._logger = SimpleNamespace(info=lambda *a, **k: None)

    # default format_messages that returns a serializable object useful for assertions
    def format_messages(**kwargs):
        return {
            "thought1": kwargs.get("thought1"),
            "action1": kwargs.get("action1"),
            "thought2": kwargs.get("thought2"),
            "action2": kwargs.get("action2"),
            "use_cache_control": kwargs.get("use_cache_control"),
        }

    inst.format_messages = format_messages

    return inst


def test_binary_trajectory_comparison_single_completion_round_036():
    """When get_completions yields a single (dict-like) completion, get_action should return it
    and produce an empty comparison_log (no pairwise comparisons performed).

    The failure in the previous run showed ActionSamplerOutput expects a mapping for
    the completion value; using a dict-like completion here fixes that validation error.
    """
    model = DummyModel([])  # no responses expected because no comparisons
    tools = DummyTools()
    inst = _make_instance(model, tools, comparison_temperature=0.9)

    # make get_completions deterministic: only one completion -> loop at lines 276..301 must be skipped
    inst.get_completions = lambda history: [{"content": "only_completion"}]

    # interpret should not be called in this case, but provide a safeguard
    inst.interpret = lambda response: (_ for _ in ()).throw(AssertionError("interpret was unexpectedly called"))

    out = inst.get_action(problem_statement={}, trajectory=[], history=[])

    assert isinstance(out, ActionSamplerOutput)
    # final chosen completion must be the single provided completion mapping
    assert isinstance(out.completion, dict)
    assert out.completion.get("content") == "only_completion"
    # no comparisons were made, so comparison_log must be empty
    assert out.extra_info.get("comparison_log") == []


def test_binary_trajectory_comparison_multiple_completions_round_036():
    """With multiple completions (dict-like), get_action should perform pairwise comparisons.
    This test exercises the loop body (lines 276..300), ensures model.query is called
    with the configured temperature, and that best_idx is updated when interpret returns 1.
    """
    # configure deterministic model responses for two comparisons
    model = DummyModel(["resp_choose_0", "resp_choose_1"])
    tools = DummyTools()
    inst = _make_instance(model, tools, comparison_temperature=0.42)

    # three completions -> two comparisons: i == 1 and i == 2
    completions = [{"content": "c0"}, {"content": "c1"}, {"content": "c2"}]
    inst.get_completions = lambda history: list(completions)

    # deterministic interpret based on the exact response string returned by DummyModel
    def interpret(response):
        if response == "resp_choose_0":
            return 0
        if response == "resp_choose_1":
            return 1
        raise AssertionError(f"Unexpected response passed to interpret: {response}")

    inst.interpret = interpret

    # capture the messages produced to ensure use_cache_control toggles when len(completions) >= 3
    produced_messages = []

    def format_messages(**kwargs):
        m = {
            "thought1": kwargs.get("thought1"),
            "action1": kwargs.get("action1"),
            "thought2": kwargs.get("thought2"),
            "action2": kwargs.get("action2"),
            "use_cache_control": kwargs.get("use_cache_control"),
        }
        produced_messages.append(m)
        return m

    inst.format_messages = format_messages

    # Run the method under test
    out = inst.get_action(problem_statement={}, trajectory=[], history=[])

    # After first comparison (0 vs 1), interpret returned 0 -> best_idx remains 0
    # After second comparison (0 vs 2), interpret returned 1 -> best_idx becomes 2
    assert isinstance(out.completion, dict)
    assert out.completion.get("content") == "c2"

    # Validate comparison_log contents
    log = out.extra_info.get("comparison_log")
    assert isinstance(log, list) and len(log) == 2
    assert log[0]["comparison_between"] == (0, 1)
    assert log[0]["idx"] == 0
    assert log[1]["comparison_between"] == (0, 2)
    assert log[1]["idx"] == 1

    # Ensure model.query was called the expected number of times and with configured temperature
    assert len(model.calls) == 2
    assert model.calls[0]["temperature"] == 0.42
    assert model.calls[1]["temperature"] == 0.42

    # Also ensure that format_messages was called and that use_cache_control was True because len(completions) >= 3
    assert produced_messages[0]["use_cache_control"] is True
    assert produced_messages[1]["use_cache_control"] is True
