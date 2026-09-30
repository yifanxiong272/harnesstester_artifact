import pytest

from sweagent.agent.action_sampler import AskColleagues, ActionSamplerOutput
from sweagent.exceptions import FormatError


class _FakeTools:
    """Deterministic fake ToolHandler with a controllable parse_actions behavior."""

    def __init__(self, good_keys=None):
        # completions whose 'kind' is in good_keys will parse; others raise FormatError
        self.good_keys = set(good_keys or {"good"})

    def parse_actions(self, completion: dict):
        # Expect completion to be a dict with a 'kind' key for determinism in tests
        kind = completion.get("kind")
        if kind in self.good_keys:
            # return a deterministic (thought, action) pair
            return (f"Thought for {kind}", f"action_for_{kind}()")
        raise FormatError("unparseable completion")


class _FakeModel:
    """Deterministic fake model. query(...) returns different values depending on kwargs.

    - If called with n=..., returns a list of completions (dictionaries).
    - Otherwise returns a final completion string.
    It also verifies that the second call receives the discussion message produced by
    AskColleagues.get_colleague_discussion.
    """

    def __init__(self, first_response_completions, final_completion):
        self.first_response_completions = first_response_completions
        self.final_completion = final_completion
        self.calls = []

    def query(self, history, n=None):
        # record a shallow copy for inspection
        self.calls.append((list(history), n))
        if n is not None:
            # first query: return the completions list
            return self.first_response_completions
        # second query: return the final completion (string or dict as used by code)
        return self.final_completion


def test_get_colleague_discussion_mixed_round_015():
    """Verify get_colleague_discussion concatenates parsable completions and skips bad ones,
    and that it raises FormatError when none are parseable.
    """
    tools = _FakeTools(good_keys={"good"})
    # config can be a simple object with .n_samples attr; not used by get_colleague_discussion
    config = type("C", (), {"n_samples": 1})()
    sampler = AskColleagues(config=config, model=None, tools=tools)

    # Mixed completions: first parses, second raises FormatError inside parse_actions
    completions = [
        {"kind": "good", "text": "ok"},
        {"kind": "bad", "text": "broken"},
    ]

    discussion = sampler.get_colleague_discussion(completions)

    # Basic structural assertions
    assert discussion.startswith("Your colleagues had the following ideas:"), "header missing"

    # Should include the parsed colleague (index 0) and its thought/action
    assert "Thought (colleague 0): Thought for good" in discussion
    assert "Proposed Action (colleague 0): action_for_good()" in discussion

    # The broken completion should be skipped (no 'colleague 1' block)
    assert "colleague 1" not in discussion

    # The closing instruction text must be present
    assert "Please summarize and compare the ideas" in discussion

    # Now assert that when no completions parse, a FormatError is raised
    bad_only = [{"kind": "bad1"}, {"kind": "bad2"}]
    with pytest.raises(FormatError):
        sampler.get_colleague_discussion(bad_only)


def test_get_action_calls_model_round_015():
    """Verify get_action uses model.query twice and returns ActionSamplerOutput with
    the final completion and colleagues discussion in extra_info.
    """
    # First response: one parseable completion
    first_completions = [{"kind": "good", "text": "ok"}]
    final_completion = {"result": "FINAL_ACTION_CALL"}

    fake_model = _FakeModel(first_response_completions=first_completions, final_completion=final_completion)
    tools = _FakeTools(good_keys={"good"})
    config = type("C", (), {"n_samples": 1})()

    sampler = AskColleagues(config=config, model=fake_model, tools=tools)

    # Provide minimal arguments for get_action; problem_statement and trajectory are not used by our fakes
    result = sampler.get_action(problem_statement=None, trajectory=None, history=[{"role": "user", "content": "start"}])

    # Returned object type and fields
    assert isinstance(result, ActionSamplerOutput)
    assert result.completion == final_completion

    # The colleagues discussion should be included in extra_info
    colleagues_text = result.extra_info.get("colleagues")
    assert isinstance(colleagues_text, str)
    assert "Your colleagues had the following ideas" in colleagues_text

    # Ensure the model was queried twice: first with n set, then without
    assert len(fake_model.calls) >= 2
    first_call_history, first_call_n = fake_model.calls[0]
    second_call_history, second_call_n = fake_model.calls[1]

    # First call should include the original history and a provided n
    assert first_call_n == config.n_samples
    assert any(m.get("role") == "user" and m.get("content") == "start" for m in first_call_history)

    # Second call should not include n and should receive the discussion as an added user message
    assert second_call_n is None
    # The last message in the second call history should be the discussion generated by the sampler
    assert any(m.get("role") == "user" and isinstance(m.get("content"), str) and m.get("content").startswith("Your colleagues had the following ideas") for m in second_call_history)
