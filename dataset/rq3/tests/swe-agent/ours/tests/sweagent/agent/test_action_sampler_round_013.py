import pytest
from types import SimpleNamespace

from sweagent.agent.action_sampler import AskColleagues, ActionSamplerOutput
from sweagent.exceptions import FormatError


def test_get_colleague_discussion_all_parsed_round_013():
    # Tools that successfully parse each completion into (thought, action)
    tools = SimpleNamespace(parse_actions=lambda completion: (completion["thought"], completion["action"]))
    model = SimpleNamespace()  # not used for this unit
    config = SimpleNamespace(n_samples=1)

    sampler = AskColleagues(config, model, tools)

    completions = [
        {"thought": "We could cache results.", "action": "call_cache_tool"},
        {"thought": "We could parallelize.", "action": "call_parallel_tool"},
    ]

    discussion = sampler.get_colleague_discussion(completions)

    # Check that each colleague's thought and action are present
    assert "Thought (colleague 0): We could cache results." in discussion
    assert "Proposed Action (colleague 0): call_cache_tool" in discussion
    assert "Thought (colleague 1): We could parallelize." in discussion
    assert "Proposed Action (colleague 1): call_parallel_tool" in discussion

    # Ensure the instruction/prompt text asking for a thought and action is appended
    assert "You must include a thought and action" in discussion
    # Also check the leading header is present
    assert discussion.startswith("Your colleagues had the following ideas:")


def test_get_colleague_discussion_none_parsed_raises_round_013():
    # Tools that always fail to parse -> raise FormatError
    def parse_actions_raise(completion):
        raise FormatError("unparseable")

    tools = SimpleNamespace(parse_actions=parse_actions_raise)
    model = SimpleNamespace()
    config = SimpleNamespace(n_samples=1)

    sampler = AskColleagues(config, model, tools)

    completions = [{"foo": "bar"}, {"baz": "qux"}]

    with pytest.raises(FormatError) as exc:
        sampler.get_colleague_discussion(completions)

    # The implementation raises a FormatError with an exact explanatory message
    assert str(exc.value) == "No completions could be parsed."


def test_get_action_calls_model_and_returns_output_round_013():
    # This fake model records calls and returns deterministic values.
    calls = []

    def query(arg, **kwargs):
        # Record the call (copy kwargs to avoid mutation issues)
        calls.append((arg, dict(kwargs)))
        # First call: called with history and n=... -> return a list of completions
        if "n" in kwargs:
            # Return completions that parse into a single colleague thought/action
            return [{"thought": "Consider retrying.", "action": "retry_tool"}]
        # Second call: final completion returned (simulating model final answer)
        return {"final": "recommended_action", "tool_call": "retry_tool"}

    model = SimpleNamespace(query=query)

    # Tools parse actions deterministically from the completion dicts
    tools = SimpleNamespace(parse_actions=lambda completion: (completion["thought"], completion["action"]))

    config = SimpleNamespace(n_samples=2)
    sampler = AskColleagues(config, model, tools)

    # A minimal history passed to get_action
    history = [{"role": "user", "content": "Please solve X"}]

    result = sampler.get_action(problem_statement=None, trajectory=None, history=history)

    # The result should be an ActionSamplerOutput and carry the final completion
    assert isinstance(result, ActionSamplerOutput)
    assert result.completion == {"final": "recommended_action", "tool_call": "retry_tool"}

    # The colleagues discussion should be included in extra_info and mention the parsed thought
    colleagues_text = result.extra_info["colleagues"]
    assert "Thought (colleague 0): Consider retrying." in colleagues_text
    assert "Proposed Action (colleague 0): retry_tool" in colleagues_text

    # Ensure model.query was called twice: once with n=2, once with the augmented history
    assert len(calls) == 2
    # First call included the n parameter
    assert calls[0][1].get("n") == 2
    # The second call's first argument is history + new_messages where new_messages is a single dict
    second_call_arg = calls[1][0]
    assert isinstance(second_call_arg, list)
    # The original history should be the prefix
    assert second_call_arg[0] == history[0]
    # The appended message should be a user message with the colleagues discussion as content
    appended = second_call_arg[1]
    assert appended["role"] == "user"
    assert isinstance(appended["content"], str)
    assert "Thought (colleague 0):" in appended["content"]
