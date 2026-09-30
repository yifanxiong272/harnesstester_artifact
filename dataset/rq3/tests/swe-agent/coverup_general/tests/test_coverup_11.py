# file: sweagent/agent/action_sampler.py:49-93
# asked: {"lines": [51, 52, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 74, 83, 84, 85, 86, 87, 89, 90, 91, 92], "branches": [[58, 59], [58, 66], [66, 67], [66, 69]]}
# gained: {"lines": [51, 52, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 74, 83, 84, 85, 86, 87, 89, 90, 91, 92], "branches": [[58, 59], [58, 66], [66, 67], [66, 69]]}

import pytest
from types import SimpleNamespace
from sweagent.agent.action_sampler import AskColleagues
from sweagent.exceptions import FormatError


class FakeTools:
    def __init__(self, behavior):
        self._behavior = behavior

    def parse_actions(self, completion):
        return self._behavior(completion)


def test_get_colleague_discussion_mixed_parsing_and_warning(monkeypatch):
    # behavior: first completion raises FormatError, second parses correctly
    def behavior(c):
        if c.get("bad"):
            raise FormatError("bad completion")
        return (f"thought-{c['id']}", f"action-{c['id']}")

    tools = FakeTools(behavior)
    config = SimpleNamespace(n_samples=2)
    model = SimpleNamespace()  # model not used in this test
    ac = AskColleagues(config, model, tools)

    warnings = []

    # Replace the instance logger's warning to capture calls
    ac._logger = SimpleNamespace(
        warning=lambda *args, **kwargs: warnings.append((args, kwargs))
    )

    completions = [{"bad": True}, {"id": "ok"}]

    discussion = ac.get_colleague_discussion(completions)

    # The parsed completion (index 1) should be included
    assert "Thought (colleague 1): thought-ok" in discussion
    assert "Proposed Action (colleague 1): action-ok" in discussion

    # The header and the final instruction block should be present
    assert discussion.startswith("Your colleagues had the following ideas:")
    assert "Please summarize and compare the ideas" in discussion
    assert "<important>You must include a thought and action" in discussion

    # A warning should have been emitted for the unparsable completion
    assert len(warnings) == 1
    # The first element of the warning tuple is the format string and the completion object
    warning_args, _ = warnings[0]
    assert "Could not parse completion" in warning_args[0]


def test_get_colleague_discussion_all_unparseable_raises(monkeypatch):
    # parse_actions always raises -> get_colleague_discussion should raise FormatError
    def behavior(_c):
        raise FormatError("always bad")

    tools = FakeTools(behavior)
    config = SimpleNamespace(n_samples=1)
    model = SimpleNamespace()
    ac = AskColleagues(config, model, tools)

    # Provide a logger that would be used if called (not strictly necessary)
    ac._logger = SimpleNamespace(warning=lambda *a, **k: None)

    with pytest.raises(FormatError) as excinfo:
        ac.get_colleague_discussion([{"a": 1}, {"b": 2}])

    assert "No completions could be parsed." in str(excinfo.value)


def test_get_action_uses_model_queries_and_returns_output(monkeypatch):
    # Prepare two completions for the colleague discussion (first model.query call)
    completions = [{"id": "a"}, {"id": "b"}]
    final_completion = {"result": "final"}

    calls = []

    class FakeModel:
        def query(self, *args, **kwargs):
            # Record call for assertions
            calls.append((args, kwargs))
            # First call includes 'n' -> return list of completions
            if "n" in kwargs:
                return completions
            # Second call (no 'n') -> return final completion
            return final_completion

    # parse_actions will succeed for both completions
    def behavior(c):
        return (f"thought-{c['id']}", f"action-{c['id']}")

    tools = FakeTools(behavior)
    config = SimpleNamespace(n_samples=3)
    model = FakeModel()
    ac = AskColleagues(config, model, tools)

    infos = []
    ac._logger = SimpleNamespace(
        info=lambda msg: infos.append(msg),
        warning=lambda *a, **k: None,
    )

    history = [{"role": "user", "content": "start"}]

    output = ac.get_action(None, None, history)

    # Ensure the returned completion is the final completion from the second query
    assert output.completion == final_completion

    # extra_info should contain the colleague discussion string
    assert isinstance(output.extra_info, dict)
    discussion = output.extra_info.get("colleagues")
    assert isinstance(discussion, str)
    assert "Your colleagues had the following ideas" in discussion
    assert "Thought (colleague 0): thought-a" in discussion
    assert "Thought (colleague 1): thought-b" in discussion

    # Ensure model.query was called first with n=config.n_samples
    assert any(kwargs.get("n") == 3 for (_, kwargs) in calls)

    # Ensure the second query was made with history + new_messages (history length + 1)
    # It's the last recorded call
    last_args, last_kwargs = calls[-1]
    assert len(last_args) >= 1
    sent_history = last_args[0]
    assert isinstance(sent_history, list)
    assert len(sent_history) == len(history) + 1
    assert any("COLLEAGUE DISCUSSION" in s for s in infos)
