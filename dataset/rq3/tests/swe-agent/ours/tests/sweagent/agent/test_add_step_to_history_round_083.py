import builtins
import types
import pytest
from sweagent.agent.agents import DefaultAgent


class SimpleStep:
    def __init__(self, *, output, thought, action, tool_calls, observation, tool_call_ids, state):
        # mirror the attributes accessed by DefaultAgent.add_step_to_history
        self.output = output
        self.thought = thought
        self.action = action
        self.tool_calls = tool_calls
        self.observation = observation
        self.tool_call_ids = tool_call_ids
        self.state = state


class DummyTemplates:
    def __init__(self, max_observation_length=10):
        self.next_step_truncated_observation_template = "TRUNCATED_TEMPLATE"
        self.next_step_no_output_template = "NO_OUTPUT_TEMPLATE"
        self.next_step_template = "STANDARD_TEMPLATE"
        self.max_observation_length = max_observation_length


def make_agent_with_templates(max_observation_length=10):
    # create a DefaultAgent instance without calling its heavy __init__
    agent = object.__new__(DefaultAgent)
    agent.name = "test-agent"
    agent.templates = DummyTemplates(max_observation_length=max_observation_length)
    return agent


def test_add_step_to_history_truncates_observation_round_083():
    agent = make_agent_with_templates(max_observation_length=10)

    appended = {}

    def fake_append_history(item):
        # capture the dict that _append_history is given
        appended['item'] = item

    templated_called = {}

    def fake_add_templated_messages_to_history(templates, *, observation, elided_chars, max_observation_length, tool_call_ids, **state_kwargs):
        # capture all incoming values for assertions
        templated_called['templates'] = templates
        templated_called['observation'] = observation
        templated_called['elided_chars'] = elided_chars
        templated_called['max_observation_length'] = max_observation_length
        templated_called['tool_call_ids'] = tool_call_ids
        templated_called['state_kwargs'] = state_kwargs

    # patch the instance methods
    agent._append_history = fake_append_history
    agent._add_templated_messages_to_history = fake_add_templated_messages_to_history

    original_obs = "X" * 15
    step = SimpleStep(
        output="cmd-output",
        thought="some-thought",
        action="some-action",
        tool_calls=[],
        observation=original_obs,
        tool_call_ids=["tc1"],
        state={"k": "v"},
    )

    # call the function under test
    agent.add_step_to_history(step)

    # Assertions for _append_history call
    assert 'item' in appended, "_append_history was not called"
    ah = appended['item']
    assert ah['role'] == 'assistant'
    assert ah['content'] == 'cmd-output'
    assert ah['thought'] == 'some-thought'
    assert ah['action'] == 'some-action'
    assert ah['agent'] == 'test-agent'
    assert ah['tool_calls'] == []
    assert ah['message_type'] == 'action'

    # Assertions for truncated-observation branch
    assert 'templates' in templated_called, "_add_templated_messages_to_history was not called"
    assert templated_called['templates'] == [agent.templates.next_step_truncated_observation_template]
    # observation should have been truncated to max_observation_length
    assert templated_called['observation'] == original_obs[: agent.templates.max_observation_length]
    # elided_chars should be original_len - max_len
    assert templated_called['elided_chars'] == len(original_obs) - agent.templates.max_observation_length
    assert templated_called['max_observation_length'] == agent.templates.max_observation_length
    assert templated_called['tool_call_ids'] == ["tc1"]
    assert templated_called['state_kwargs'] == {"k": "v"}


def test_add_step_to_history_empty_observation_uses_no_output_template_round_083():
    agent = make_agent_with_templates(max_observation_length=10)

    appended = {}

    def fake_append_history(item):
        appended['item'] = item

    templated_called = {}

    def fake_add_templated_messages_to_history(templates, *, observation, elided_chars, max_observation_length, tool_call_ids, **state_kwargs):
        templated_called['templates'] = templates
        templated_called['observation'] = observation
        templated_called['elided_chars'] = elided_chars
        templated_called['max_observation_length'] = max_observation_length
        templated_called['tool_call_ids'] = tool_call_ids
        templated_called['state_kwargs'] = state_kwargs

    agent._append_history = fake_append_history
    agent._add_templated_messages_to_history = fake_add_templated_messages_to_history

    # observation that is whitespace only should be treated as empty
    obs = "   "
    step = SimpleStep(
        output="out",
        thought="t",
        action="a",
        tool_calls=[],
        observation=obs,
        tool_call_ids=[],
        state={},
    )

    agent.add_step_to_history(step)

    # verify append_history saw the expected fields
    assert appended['item']['content'] == 'out'
    # verify the no-output template was chosen
    assert templated_called['templates'] == [agent.templates.next_step_no_output_template]
    # elided chars should be zero for empty observation branch
    assert templated_called['elided_chars'] == 0
    # observation passed through unchanged (still whitespace)
    assert templated_called['observation'] == obs
    assert templated_called['max_observation_length'] == agent.templates.max_observation_length
