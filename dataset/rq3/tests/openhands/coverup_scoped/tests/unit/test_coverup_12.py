# file: openhands/agenthub/readonly_agent/function_calling.py:117-245
# asked: {"lines": [129, 130, 131, 132, 140, 141, 142, 143, 149, 150, 157, 158, 159, 161, 162, 164, 171, 177, 178, 179, 182, 183, 184, 186, 187, 193, 194, 195, 198, 199, 201, 202, 208, 209, 210, 219, 220, 222, 223, 224, 225, 226, 228, 230, 231, 232, 233, 241, 242, 244, 245], "branches": [[124, 230], [127, 129], [129, 130], [129, 135], [130, 131], [130, 135], [131, 130], [131, 132], [135, 241], [148, 149], [156, 157], [157, 158], [157, 161], [170, 171], [176, 177], [177, 178], [177, 182], [192, 193], [193, 194], [193, 198], [207, 208], [219, 220], [219, 222], [241, 242], [241, 244]]}
# gained: {"lines": [129, 130, 131, 132, 140, 141, 142, 143, 149, 150, 157, 158, 159, 161, 162, 164, 171, 177, 178, 179, 182, 183, 184, 186, 187, 193, 194, 195, 198, 199, 201, 202, 208, 209, 210, 219, 220, 222, 223, 224, 225, 226, 228, 230, 231, 232, 233, 241, 242, 244, 245], "branches": [[124, 230], [127, 129], [129, 130], [130, 131], [130, 135], [131, 130], [131, 132], [135, 241], [148, 149], [156, 157], [157, 158], [157, 161], [170, 171], [176, 177], [177, 178], [177, 182], [192, 193], [193, 194], [193, 198], [207, 208], [219, 220], [219, 222], [241, 242], [241, 244]]}

import json
from types import SimpleNamespace

import pytest

from openhands.agenthub.readonly_agent import function_calling as fc
from openhands.agenthub.codeact_agent.tools import FinishTool, ThinkTool
from openhands.agenthub.readonly_agent.tools import GlobTool, GrepTool, ViewTool
from openhands.events.action import (
    AgentFinishAction,
    AgentThinkAction,
    CmdRunAction,
    FileReadAction,
    MCPAction,
    MessageAction,
)
from openhands.events.event import FileReadSource
from openhands.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)


@pytest.fixture(autouse=True)
def patch_tool_call_metadata(monkeypatch):
    """Replace ToolCallMetadata in the module with a permissive dummy to avoid pydantic validation issues."""
    class DummyToolCallMetadata:
        def __init__(self, tool_call_id, function_name, model_response, total_calls_in_response):
            self.tool_call_id = tool_call_id
            self.function_name = function_name
            self.model_response = model_response
            self.total_calls_in_response = total_calls_in_response

    monkeypatch.setattr(fc, "ToolCallMetadata", DummyToolCallMetadata)
    yield


def make_response(choice_message):
    """Helper to build a simple ModelResponse-like object expected by response_to_actions."""
    return SimpleNamespace(id="resp-id", choices=[SimpleNamespace(message=choice_message)])


def make_tool_call(id_, name, arguments_dict_or_str):
    """Create an object that mimics the tool_call structure used by response_to_actions."""
    if isinstance(arguments_dict_or_str, str):
        arguments = arguments_dict_or_str
    else:
        arguments = json.dumps(arguments_dict_or_str)
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(id=id_, function=function)


def test_content_list_and_json_decode_error():
    # content as a list: should concatenate only entries with type == 'text'
    content_list = [
        {"type": "text", "text": "hello "},
        {"type": "other", "text": "ignored"},
        {"type": "text", "text": "world"},
    ]

    # create a tool_call with invalid JSON arguments to trigger JSONDecodeError -> FunctionCallValidationError
    bad_arguments = "{not: valid json,,}"
    tc = make_tool_call("tc-badjson", FinishTool["function"]["name"], bad_arguments)
    message = SimpleNamespace(content=content_list, tool_calls=[tc])
    resp = make_response(message)

    with pytest.raises(FunctionCallValidationError) as excinfo:
        fc.response_to_actions(resp)
    assert "Failed to parse tool call arguments" in str(excinfo.value)


def test_all_tool_branches_and_response_id_and_types():
    # Build a sequence of tool calls exercising Think, Grep, Glob, View, Finish, and MCP
    content_thought = "leading thought"
    tool_calls = []

    # 0: ThinkTool (first -> combine_thought should apply)
    think_args = {"thought": "inner-thought"}
    tool_calls.append(make_tool_call("tc-think", ThinkTool["function"]["name"], think_args))

    # 1: GrepTool with pattern/include/path
    grep_args = {"pattern": "TODO", "path": "src", "include": "*.py"}
    tool_calls.append(make_tool_call("tc-grep", GrepTool["function"]["name"], grep_args))

    # 2: GlobTool with pattern and path
    glob_args = {"pattern": "**/*.py", "path": "."}
    tool_calls.append(make_tool_call("tc-glob", GlobTool["function"]["name"], glob_args))

    # 3: ViewTool with path and view_range
    view_args = {"path": "/some/file.txt", "view_range": [0, 10]}
    tool_calls.append(make_tool_call("tc-view", ViewTool["function"]["name"], view_args))

    # 4: FinishTool with message
    finish_args = {"message": "done!"}
    tool_calls.append(make_tool_call("tc-finish", FinishTool["function"]["name"], finish_args))

    # 5: MCP tool (custom), name included in mcp_tool_names -> should become MCPAction
    mcp_name = "mcp_custom"
    mcp_args = {"arg1": "value1"}
    tool_calls.append(make_tool_call("tc-mcp", mcp_name, mcp_args))

    message = SimpleNamespace(content=content_thought, tool_calls=tool_calls)
    resp = make_response(message)

    actions = fc.response_to_actions(resp, mcp_tool_names=[mcp_name])

    # Expect one action per tool call
    assert len(actions) == len(tool_calls)

    # 0: ThinkTool -> AgentThinkAction, thought combined
    a0 = actions[0]
    assert isinstance(a0, AgentThinkAction)
    # combine_thought: since both content_thought and inner-thought exist -> joined with newline
    assert a0.thought == f"{content_thought}\n{think_args['thought']}"

    # 1: GrepTool -> CmdRunAction and command contains pattern and include and path
    a1 = actions[1]
    assert isinstance(a1, CmdRunAction)
    assert "rg -li" in a1.command
    assert "TODO" in a1.command
    assert "src" in a1.command
    assert "*.py" in a1.command

    # 2: GlobTool -> CmdRunAction
    a2 = actions[2]
    assert isinstance(a2, CmdRunAction)
    assert "--files" in a2.command and "-g" in a2.command and "**/*.py" in a2.command

    # 3: ViewTool -> FileReadAction
    a3 = actions[3]
    assert isinstance(a3, FileReadAction)
    assert a3.path == view_args["path"]
    assert a3.impl_source == FileReadSource.OH_ACI
    assert a3.view_range == view_args["view_range"]

    # 4: FinishTool -> AgentFinishAction with final_thought
    a4 = actions[4]
    assert isinstance(a4, AgentFinishAction)
    assert a4.final_thought == finish_args["message"]

    # 5: MCPAction -> MCPAction with given name and arguments
    a5 = actions[5]
    assert isinstance(a5, MCPAction)
    assert a5.name == mcp_name
    assert a5.arguments == mcp_args

    # Ensure response_id attached for all actions (postcondition)
    for act in actions:
        assert getattr(act, "response_id", None) == resp.id


def test_view_missing_path_raises_validation():
    tc = make_tool_call("tc-view-bad", ViewTool["function"]["name"], {"view_range": [0, 1]})
    message = SimpleNamespace(content="", tool_calls=[tc])
    resp = make_response(message)
    with pytest.raises(FunctionCallValidationError) as excinfo:
        fc.response_to_actions(resp)
    assert 'Missing required argument "path"' in str(excinfo.value)


def test_grep_missing_pattern_raises_validation():
    tc = make_tool_call("tc-grep-bad", GrepTool["function"]["name"], {"path": "src"})
    message = SimpleNamespace(content="", tool_calls=[tc])
    resp = make_response(message)
    with pytest.raises(FunctionCallValidationError) as excinfo:
        fc.response_to_actions(resp)
    assert 'Missing required argument "pattern"' in str(excinfo.value)


def test_glob_missing_pattern_raises_validation():
    tc = make_tool_call("tc-glob-bad", GlobTool["function"]["name"], {"path": "."})
    message = SimpleNamespace(content="", tool_calls=[tc])
    resp = make_response(message)
    with pytest.raises(FunctionCallValidationError) as excinfo:
        fc.response_to_actions(resp)
    assert 'Missing required argument "pattern"' in str(excinfo.value)


def test_unknown_tool_raises_not_exists():
    # tool name unknown and not in mcp list -> FunctionCallNotExistsError
    tc = make_tool_call("tc-unknown", "not_a_registered_tool", {"foo": "bar"})
    message = SimpleNamespace(content="", tool_calls=[tc])
    resp = make_response(message)
    with pytest.raises(FunctionCallNotExistsError) as excinfo:
        fc.response_to_actions(resp)
    assert "Tool not_a_registered_tool is not registered" in str(excinfo.value)


def test_message_action_when_no_tool_calls():
    # When no tool_calls attribute or empty, a MessageAction is produced
    # Case: content is None -> content becomes ''
    message_none = SimpleNamespace(content=None, tool_calls=[])
    resp_none = make_response(message_none)
    actions_none = fc.response_to_actions(resp_none)
    assert len(actions_none) == 1
    a = actions_none[0]
    assert isinstance(a, MessageAction)
    assert a.content == ""
    assert a.wait_for_response is True
    assert a.response_id == resp_none.id

    # Case: content is string
    message_str = SimpleNamespace(content="just a message", tool_calls=[])
    resp_str = make_response(message_str)
    actions_str = fc.response_to_actions(resp_str)
    assert len(actions_str) == 1
    a2 = actions_str[0]
    assert isinstance(a2, MessageAction)
    assert a2.content == "just a message"
    assert a2.wait_for_response is True
    assert a2.response_id == resp_str.id
