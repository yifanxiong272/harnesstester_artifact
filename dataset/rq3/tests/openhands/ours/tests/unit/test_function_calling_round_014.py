import json
from types import SimpleNamespace
import pytest

import openhands.agenthub.readonly_agent.function_calling as function_calling

# Create lightweight dummy action classes and metadata to avoid importing heavy domain models
class DummyAction:
    def __init__(self, **kwargs):
        # store everything passed for assertions
        self._kwargs = kwargs
        # allow assignment of tool_call_metadata and response_id from function under test
        self.tool_call_metadata = None
        self.response_id = None

    def __repr__(self):
        return f"DummyAction({self._kwargs})"

class DummyToolCallMetadata:
    def __init__(self, tool_call_id, function_name, model_response, total_calls_in_response):
        self.tool_call_id = tool_call_id
        self.function_name = function_name
        self.model_response = model_response
        self.total_calls_in_response = total_calls_in_response


@pytest.fixture(autouse=True)
def patch_action_classes(monkeypatch):
    """Patch the action constructors and ToolCallMetadata resolved inside the module under test.
    This ensures deterministic, lightweight objects and that combine_thought behavior is controlled.
    """
    # Patch action classes to our DummyAction so we can inspect created instances
    monkeypatch.setattr(function_calling, 'AgentFinishAction', lambda **kwargs: DummyAction(kind='finish', **kwargs))
    monkeypatch.setattr(function_calling, 'FileReadAction', lambda **kwargs: DummyAction(kind='fileread', **kwargs))
    monkeypatch.setattr(function_calling, 'AgentThinkAction', lambda **kwargs: DummyAction(kind='think', **kwargs))
    monkeypatch.setattr(function_calling, 'CmdRunAction', lambda **kwargs: DummyAction(kind='cmdrun', **kwargs))
    monkeypatch.setattr(function_calling, 'MCPAction', lambda **kwargs: DummyAction(kind='mcp', **kwargs))
    monkeypatch.setattr(function_calling, 'MessageAction', lambda **kwargs: DummyAction(kind='message', **kwargs))
    monkeypatch.setattr(function_calling, 'ToolCallMetadata', DummyToolCallMetadata)

    # Patch combine_thought to deterministically add a field 'combined_thought' to the action and return it.
    def _combine_thought(action, thought):
        # mutate and return same action object as original combine_thought is expected to
        setattr(action, 'combined_thought', thought)
        return action

    monkeypatch.setattr(function_calling, 'combine_thought', _combine_thought)

    yield


def make_tool_call(name: str, args_str: str, id: str = 'call-1'):
    """Helper to build an object shape expected by response_to_actions."""
    func = SimpleNamespace(name=name, arguments=args_str)
    return SimpleNamespace(id=id, function=func)


def make_choice_with_message(content, tool_calls_attr=True, tool_calls=None):
    """Return a SimpleNamespace mimicking the choice.message structure.
    If tool_calls_attr is False, the attribute is omitted (to exercise the no-tool-calls path).
    """
    msg = SimpleNamespace()
    # content may be None, str, or list
    msg.content = content
    if tool_calls_attr:
        # if provided, set the list (truthy/falsey) as requested
        msg.tool_calls = tool_calls or []
    return SimpleNamespace(message=msg)


def make_response(choice_message, resp_id='resp-1'):
    return SimpleNamespace(id=resp_id, choices=[choice_message])


def test_message_no_tool_calls_round_014():
    # A response without tool_calls attribute should go to the MessageAction branch
    choice = make_choice_with_message(content='hello world', tool_calls_attr=False)
    response = make_response(choice, resp_id='r-msg-1')

    actions = function_calling.response_to_actions(response)

    assert isinstance(actions, list)
    assert len(actions) == 1
    act = actions[0]
    # patched MessageAction constructs a DummyAction with stored kwargs
    assert act._kwargs.get('content') == 'hello world'
    assert act._kwargs.get('wait_for_response') is True
    # response_id must be propagated
    assert act.response_id == 'r-msg-1'


def test_tool_calls_with_thought_list_and_mcp_round_014():
    # Test assistant_msg.content as a list of fragments (lines 129-132) and multiple tool calls
    content_list = [
        {'type': 'text', 'text': 'thought-A '},
        {'type': 'other', 'text': 'ignored'},
        {'type': 'text', 'text': 'thought-B'},
    ]

    # Use tool names that we will treat as MCP tools by passing them in mcp_tool_names
    tc1 = make_tool_call('mcp_alpha', json.dumps({'x': 1, 'message': 'done'}), id='t1')
    tc2 = make_tool_call('mcp_beta', json.dumps({'y': 2}), id='t2')

    # Create choice/message with tool_calls present
    choice = make_choice_with_message(content=content_list, tool_calls_attr=True, tool_calls=[tc1, tc2])
    response = make_response(choice, resp_id='r-mcp-1')

    actions = function_calling.response_to_actions(response, mcp_tool_names=['mcp_alpha', 'mcp_beta'])

    # Expect two actions created (one per tool call)
    assert len(actions) == 2

    # First action should have combined_thought applied from content_list (only 'text' entries concatenated)
    first = actions[0]
    assert getattr(first, 'combined_thought') == 'thought-A thought-B'
    # Since patched MCPAction stores name and arguments in kwargs
    assert first._kwargs.get('name') == 'mcp_alpha'
    assert first._kwargs.get('arguments') == {'x': 1, 'message': 'done'}
    assert first.tool_call_metadata.function_name == 'mcp_alpha'
    assert first.tool_call_metadata.tool_call_id == 't1'
    assert first.tool_call_metadata.total_calls_in_response == 2
    assert first.response_id == 'r-mcp-1'

    # Second action should NOT have combined_thought (combine only applied to i==0)
    second = actions[1]
    assert not hasattr(second, 'combined_thought')
    assert second._kwargs.get('name') == 'mcp_beta'
    assert second._kwargs.get('arguments') == {'y': 2}
    assert second.response_id == 'r-mcp-1'


def test_invalid_json_arguments_raises_round_014():
    # When a tool_call.function.arguments is invalid JSON, FunctionCallValidationError should be raised
    bad_tc = make_tool_call('some_tool', "{not: valid, json}", id='bad1')
    choice = make_choice_with_message(content='x', tool_calls_attr=True, tool_calls=[bad_tc])
    response = make_response(choice)

    with pytest.raises(function_calling.FunctionCallValidationError):
        function_calling.response_to_actions(response)
