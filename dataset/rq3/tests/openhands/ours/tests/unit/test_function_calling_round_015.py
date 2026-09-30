import json
import pytest

from openhands.agenthub.loc_agent import function_calling
from openhands.agenthub.loc_agent.function_calling import response_to_actions
from openhands.agenthub.codeact_agent.tools import FinishTool
from openhands.core.exceptions import FunctionCallNotExistsError
from openhands.events.action import (
    IPythonRunCellAction,
    AgentFinishAction,
    MessageAction,
)


class _Choice:
    def __init__(self, message):
        self.message = message


class _FakeResponse:
    def __init__(self, choices, id_="resp-id"):
        self.choices = choices
        self.id = id_


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        # function.arguments in real code is expected to be a JSON string
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, id_, function):
        self.id = id_
        self.function = function


class _AssistantMsgNoToolCalls:
    def __init__(self, content):
        # no tool_calls attribute to hit the "else" branch
        self.content = content


class _AssistantMsgWithToolCalls:
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls


def test_message_action_no_tool_calls_round_015():
    """
    When the assistant message has no tool_calls attribute, response_to_actions should
    return a single MessageAction with content reflected and response_id set.
    """
    assistant_msg = _AssistantMsgNoToolCalls(content="hello world")
    resp = _FakeResponse(choices=[_Choice(assistant_msg)], id_="r1")

    actions = response_to_actions(resp)

    assert len(actions) == 1
    act = actions[0]
    assert isinstance(act, MessageAction)
    # content converted to str if present
    assert act.content == "hello world"
    assert getattr(act, "wait_for_response", None) is True
    # response_id should be propagated
    assert act.response_id == "r1"


def test_tool_calls_all_functions_and_finish_and_metadata_round_015(monkeypatch):
    """
    Create two tool calls: first is an ALL_FUNCTIONS entry (uses IPythonRunCellAction),
    second is the FinishTool. Ensure thoughts from content (as list) are combined only
    into the first action and that metadata + response_id are set for each action.
    """
    # Prepare content as list containing text and non-text pieces
    content = [
        {"type": "text", "text": "hello "},
        {"type": "other", "text": "ignore"},
        {"type": "text", "text": "world"},
    ]

    # First tool call: an ALL_FUNCTIONS name
    first_fn_name = "search_code_snippets"
    first_args = {"q": "value"}
    first_fn = _FakeFunction(name=first_fn_name, arguments=json.dumps(first_args))
    first_tool_call = _FakeToolCall(id_="t1", function=first_fn)

    # Second tool call: FinishTool
    finish_name = FinishTool["function"]["name"]
    second_args = {"message": "done message"}
    second_fn = _FakeFunction(name=finish_name, arguments=json.dumps(second_args))
    second_tool_call = _FakeToolCall(id_="t2", function=second_fn)

    assistant_msg = _AssistantMsgWithToolCalls(content=content, tool_calls=[first_tool_call, second_tool_call])
    resp = _FakeResponse(choices=[_Choice(assistant_msg)], id_="r-xyz")

    # Patch combine_thought to annotate the action rather than relying on real implementation
    recorded = {}

    def _fake_combine_thought(action, thought):
        # record that combine_thought was invoked with expected thought
        recorded['thought'] = thought
        # annotate action to make assertion easier
        setattr(action, 'combined_thought', thought)
        return action

    monkeypatch.setattr(function_calling, 'combine_thought', _fake_combine_thought)

    actions = response_to_actions(resp)

    # We expect two actions
    assert len(actions) == 2

    # First action should be IPythonRunCellAction and have been combined with thought
    first_action = actions[0]
    assert isinstance(first_action, IPythonRunCellAction)
    # The code string should reference the function name and arguments dict representation
    assert first_fn_name in getattr(first_action, 'code')
    assert "print(" in getattr(first_action, 'code')
    # combine_thought should have been called and the action annotated
    assert 'thought' in recorded
    assert getattr(first_action, 'combined_thought') == recorded['thought']
    # The thought should come from content list: 'hello world'
    assert recorded['thought'] == 'hello world'

    # Second action should be AgentFinishAction with final_thought equal to provided message
    second_action = actions[1]
    assert isinstance(second_action, AgentFinishAction)
    # AgentFinishAction stores final_thought attribute per the implementation
    assert getattr(second_action, 'final_thought') == 'done message'

    # Both actions should have tool_call_metadata with expected fields and response_id
    for idx, tool_call in enumerate([first_tool_call, second_tool_call]):
        act = actions[idx]
        meta = getattr(act, 'tool_call_metadata')
        assert meta.tool_call_id == tool_call.id
        assert meta.function_name == tool_call.function.name
        assert meta.model_response is resp
        assert meta.total_calls_in_response == 2
        assert act.response_id == resp.id


def test_json_parse_error_raises_runtime_round_015():
    """
    If the tool call function.arguments is invalid JSON, a RuntimeError should be raised
    with a helpful message.
    """
    bad_fn = _FakeFunction(name="search_code_snippets", arguments="not-a-json")
    bad_tool_call = _FakeToolCall(id_="b1", function=bad_fn)
    assistant_msg = _AssistantMsgWithToolCalls(content="irrelevant", tool_calls=[bad_tool_call])
    resp = _FakeResponse(choices=[_Choice(assistant_msg)], id_="badresp")

    with pytest.raises(RuntimeError) as ei:
        response_to_actions(resp)
    # The raised RuntimeError should mention the failed arguments string
    assert "not-a-json" in str(ei.value)


def test_unknown_function_raises_FunctionCallNotExistsError_round_015():
    """
    A tool call with a name not in ALL_FUNCTIONS and not the FinishTool should raise
    FunctionCallNotExistsError.
    """
    unknown_fn = _FakeFunction(name="completely_unknown_tool", arguments=json.dumps({}))
    unknown_tool_call = _FakeToolCall(id_="u1", function=unknown_fn)
    assistant_msg = _AssistantMsgWithToolCalls(content="x", tool_calls=[unknown_tool_call])
    resp = _FakeResponse(choices=[_Choice(assistant_msg)], id_="u-resp")

    with pytest.raises(FunctionCallNotExistsError):
        response_to_actions(resp)
