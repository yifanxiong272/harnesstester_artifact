# file: sweagent/api/hooks.py:120-152
# asked: {"lines": [123, 124, 125, 128, 129, 130, 131, 132, 133, 134, 135, 140, 141, 142, 145, 146, 147, 148, 150, 151, 152], "branches": [[129, 130], [129, 131], [146, 147], [146, 148], [148, 150], [148, 151]]}
# gained: {"lines": [123, 124, 125, 128, 129, 130, 131, 132, 133, 134, 135, 140, 141, 142, 145, 146, 147, 148, 150, 151, 152], "branches": [[129, 130], [129, 131], [146, 147], [146, 148], [148, 150], [148, 151]]}

import pytest

from sweagent.api.hooks import AgentUpdateHook


class DummyWU:
    def __init__(self):
        self.agent_calls = []
        self.env_calls = []

    def up_agent(self, *args, **kwargs):
        # Record both positional and keyword for robust assertions
        self.agent_calls.append((args, kwargs))

    def up_env(self, *args, **kwargs):
        self.env_calls.append((args, kwargs))


def test_on_actions_generated_strips_prefixes_and_increments():
    wu = DummyWU()
    hook = AgentUpdateHook(wu)

    # initial thought_idx should be 0; after call it should increment to 1
    thought = "DISCUSSION\nTHOUGHT\nThis is a thought"
    hook.on_actions_generated(thought=thought, action="act", output="out")

    # one up_agent call recorded
    assert len(wu.agent_calls) == 1
    args, kwargs = wu.agent_calls[0]
    # message should have both prefixes removed
    assert kwargs.get("message") == "This is a thought"
    assert kwargs.get("format") == "markdown"
    assert kwargs.get("thought_idx") == 1
    assert kwargs.get("type_") == "thought"

    # internal counter incremented
    # call again to ensure incrementing continues; thought_idx becomes 2
    hook.on_actions_generated(thought="THOUGHTAnother", action="", output="")
    assert len(wu.agent_calls) == 2
    _, kwargs2 = wu.agent_calls[1]
    assert kwargs2["thought_idx"] == 2
    # "THOUGHT" prefix removed leaving "Another"
    assert kwargs2["message"] == "Another"


def test_on_sub_action_started_and_executed_non_submit():
    wu = DummyWU()
    hook = AgentUpdateHook(wu)

    # Start a sub-action with surrounding whitespace
    sub = {"action": "  ls -la  "}
    hook.on_sub_action_started(sub_action=sub)

    # up_env should have been called once for the command
    assert len(wu.env_calls) == 1
    args, kwargs = wu.env_calls[0]
    assert kwargs.get("message") == "$ ls -la"  # prefixed with "$ " and stripped
    # thought_idx should be current value (0, since we haven't generated thoughts)
    assert kwargs.get("thought_idx") == 0
    assert kwargs.get("type_") == "command"
    # internal _sub_action saved without whitespace
    assert hook._sub_action == "ls -la"

    # Execute the sub-action with a non-submit action and non-None obs
    hook.on_sub_action_executed(obs="  some output text  ", done=False)

    # There should be a second env call for the output
    assert len(wu.env_calls) == 2
    _, kwargs2 = wu.env_calls[1]
    assert kwargs2.get("message") == "some output text"  # stripped
    assert kwargs2.get("type_") == "output"
    # thought_idx remains the same
    assert kwargs2.get("thought_idx") == 0


def test_on_sub_action_executed_submit_with_none_obs():
    wu = DummyWU()
    hook = AgentUpdateHook(wu)

    # Start a 'submit' sub-action
    hook.on_sub_action_started(sub_action={"action": " submit "})
    assert hook._sub_action == "submit"
    # clear any initial env call recorded
    wu.env_calls.clear()

    # Execute with obs=None to trigger obs = "" branch and type_="diff"
    hook.on_sub_action_executed(obs=None, done=True)

    assert len(wu.env_calls) == 1
    _, kwargs = wu.env_calls[0]
    # obs was None -> becomes empty string -> stripped remains ""
    assert kwargs.get("message") == ""
    assert kwargs.get("type_") == "diff"
    # thought_idx still present as an int
    assert isinstance(kwargs.get("thought_idx"), int)
