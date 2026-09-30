# file: sweagent/agent/action_sampler.py:49-93
# asked: {"lines": [51, 52, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 74, 83, 84, 85, 86, 87, 89, 90, 91, 92], "branches": [[58, 59], [58, 66], [66, 67], [66, 69]]}
# gained: {"lines": [51, 52, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 74, 83, 84, 85, 86, 87, 89, 90, 91, 92], "branches": [[58, 59], [58, 66], [66, 67], [66, 69]]}

import pytest

from sweagent.agent.action_sampler import AskColleagues
from sweagent.agent.action_sampler import AskColleaguesConfig
from sweagent.exceptions import FormatError
from typing import Any


class FakeToolsAllBad:
    """Tool handler that always fails to parse actions (raises FormatError)."""

    def parse_actions(self, output: dict) -> tuple[str, str]:
        raise FormatError("cannot parse")


class FakeToolsMixed:
    """Tool handler that raises for dicts with key 'bad'==True, otherwise returns thought/action."""

    def parse_actions(self, output: dict) -> tuple[str, str]:
        if output.get("bad"):
            raise FormatError("bad completion")
        # return deterministic thought/action derived from the content for testing
        content = output.get("content", "default")
        return f"thought-{content}", f"action-{content}"


class FakeModel:
    """A fake model that returns a list of completions when called with n, and a final completion otherwise."""

    def __init__(self):
        self.last_query_args = None

    def query(self, history: list[dict[str, Any]], n: int | None = None):
        # record calls for assertions
        # copy history shallowly to avoid test-side mutation issues
        self.last_query_args = {"history": list(history), "n": n}
        if n is not None:
            # return n completions; provide content values for deterministic parsing
            return [{"content": f"c{i}"} for i in range(n)]
        else:
            # final completion: echo back the last user message for verification
            last = history[-1] if history else {}
            return {"final": True, "echo": last.get("content")}


def test_get_colleague_discussion_all_unparsable_raises():
    """If no completion can be parsed, get_colleague_discussion should raise FormatError with expected message."""
    tools = FakeToolsAllBad()
    model = FakeModel()
    config = AskColleaguesConfig()  # default n_samples=2
    sampler = AskColleagues(config=config, model=model, tools=tools)

    completions = [{"content": "a"}, {"content": "b"}]
    with pytest.raises(FormatError) as exc:
        sampler.get_colleague_discussion(completions)

    assert "No completions could be parsed." in str(exc.value)


def test_get_colleague_discussion_mixed_parsing_includes_parsed_and_skips_bad():
    """Mixed completions: one unparsable should be skipped, parsed ones included, and final prompt appended."""
    tools = FakeToolsMixed()
    model = FakeModel()
    config = AskColleaguesConfig()
    sampler = AskColleagues(config=config, model=model, tools=tools)

    completions = [
        {"bad": True, "content": "should_skip"},
        {"content": "ok1"},
        {"content": "ok2"},
    ]

    out = sampler.get_colleague_discussion(completions)

    # Must start with the header
    assert out.startswith("Your colleagues had the following ideas:")

    # Should contain parsed thoughts/actions for colleague indices 1 and 2 (0 was skipped)
    assert "Thought (colleague 1): thought-ok1" in out
    assert "Proposed Action (colleague 1): action-ok1" in out
    assert "Thought (colleague 2): thought-ok2" in out
    assert "Proposed Action (colleague 2): action-ok2" in out

    # Should contain the final instruction sentence fragment that AskColleagues appends
    assert "Please summarize and compare the ideas" in out
    assert "You must include a thought and action" in out or "<important>You must include a thought" in out


def test_get_action_calls_model_with_samples_and_returns_output_and_extra_info():
    """Test that get_action uses model.query with n_samples, constructs discussion, and returns ActionSamplerOutput
    with the final completion and extra_info containing the colleagues discussion."""
    # Use tools that parse successfully
    tools = FakeToolsMixed()
    model = FakeModel()
    config = AskColleaguesConfig(n_samples=3)
    sampler = AskColleagues(config=config, model=model, tools=tools)

    # prepare a fake history
    history = [{"role": "user", "content": "initial"}]

    # Call get_action; it should:
    # - call model.query(history, n=config.n_samples) -> list of 3 completions
    # - build discussion from those completions
    # - call model.query(history + new_messages) without n to get final_completion
    out = sampler.get_action(problem_statement=None, trajectory=[], history=history)

    # The model must have been called; check recorded last_query_args (final call)
    assert model.last_query_args is not None
    # Final call has n=None
    assert model.last_query_args["n"] is None

    # The final completion returned by FakeModel echoes the last user message; verify ActionSamplerOutput.content
    assert isinstance(out.completion, dict)
    assert out.completion.get("final") is True

    # The last user message passed to final query should be the discussion inserted by get_action
    final_history = model.last_query_args["history"]
    assert final_history, "final history should not be empty"
    last_msg = final_history[-1]
    assert last_msg["role"] == "user"
    assert "Your colleagues had the following ideas" in last_msg["content"]

    # extra_info must contain the colleagues discussion identical to the inserted message
    assert "colleagues" in out.extra_info
    assert out.extra_info["colleagues"] == last_msg["content"]
