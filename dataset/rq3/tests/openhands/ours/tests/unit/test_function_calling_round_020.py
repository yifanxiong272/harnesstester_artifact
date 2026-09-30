import json
import types
import pytest

from openhands.agenthub.codeact_agent import function_calling as fc

# Helper simple replacements for action classes and utilities used inside function_calling
class DummyCmdRunAction:
    def __init__(self, command, is_input=False):
        self.command = command
        self.is_input = is_input
        self._timeout = None
        self.tool_call_metadata = None
        self.response_id = None

    def set_hard_timeout(self, t: float):
        # store timeout for assertions
        self._timeout = t

class DummyIPythonRunCellAction:
    def __init__(self, code):
        self.code = code
        self.tool_call_metadata = None
        self.response_id = None

class DummyAgentDelegateAction:
    def __init__(self, agent, inputs):
        self.agent = agent
        self.inputs = inputs
        self.tool_call_metadata = None
        self.response_id = None

class DummyAgentFinishAction:
    def __init__(self, final_thought=''):
        self.final_thought = final_thought
        self.tool_call_metadata = None
        self.response_id = None

class DummyFileEditAction:
    def __init__(self, **kwargs):
        # capture kwargs so tests can inspect
        self.kwargs = kwargs
        self.tool_call_metadata = None
        self.response_id = None

class DummyFileReadAction:
    def __init__(self, path=None, impl_source=None, view_range=None):
        self.path = path
        self.impl_source = impl_source
        self.view_range = view_range
        self.tool_call_metadata = None
        self.response_id = None

class DummyAgentThinkAction:
    def __init__(self, thought=''):
        self.thought = thought
        self.tool_call_metadata = None
        self.response_id = None

class DummyCondensationRequestAction:
    def __init__(self):
        self.tool_call_metadata = None
        self.response_id = None

class DummyBrowseInteractiveAction:
    def __init__(self, browser_actions):
        self.browser_actions = browser_actions
        self.tool_call_metadata = None
        self.response_id = None

class DummyTaskTrackingAction:
    def __init__(self, command, task_list):
        self.command = command
        self.task_list = task_list
        self.tool_call_metadata = None
        self.response_id = None

class DummyMCPAction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments
        self.tool_call_metadata = None
        self.response_id = None

class DummyMessageAction:
    def __init__(self, content='', wait_for_response=False):
        self.content = content
        self.wait_for_response = wait_for_response
        self.tool_call_metadata = None
        self.response_id = None

class DummyToolCallMetadata:
    def __init__(self, tool_call_id, function_name, model_response, total_calls_in_response):
        self.tool_call_id = tool_call_id
        self.function_name = function_name
        self.model_response = model_response
        self.total_calls_in_response = total_calls_in_response

# Patch the function_calling module's classes/utilities so tests don't depend on external implementations
fc.CmdRunAction = DummyCmdRunAction
fc.IPythonRunCellAction = DummyIPythonRunCellAction
fc.AgentDelegateAction = DummyAgentDelegateAction
fc.AgentFinishAction = DummyAgentFinishAction
fc.FileEditAction = DummyFileEditAction
fc.FileReadAction = DummyFileReadAction
fc.AgentThinkAction = DummyAgentThinkAction
fc.CondensationRequestAction = DummyCondensationRequestAction
fc.BrowseInteractiveAction = DummyBrowseInteractiveAction
fc.TaskTrackingAction = DummyTaskTrackingAction
fc.MCPAction = DummyMCPAction
fc.MessageAction = DummyMessageAction
fc.ToolCallMetadata = DummyToolCallMetadata

# simple combine_thought: set attribute and return
def _combine_thought(action, thought):
    setattr(action, 'thought', thought)
    return action

fc.combine_thought = _combine_thought
# set_security_risk no-op for tests
fc.set_security_risk = lambda action, args: None

# Minimal helper to construct a ModelResponse-like object expected by response_to_actions
class DummyFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class DummyToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = DummyFunction(name, arguments)

class DummyChoiceMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

class DummyChoice:
    def __init__(self, message):
        self.message = message

class DummyModelResponse:
    def __init__(self, id, choices):
        self.id = id
        self.choices = choices

# Tests

def test_cmd_run_timeout_invalid_round_020():
    """If timeout cannot be parsed as float, FunctionCallValidationError is raised."""
    # Ensure the create_cmd_run_tool used name 'cmd-run' so branch matches
    fc.create_cmd_run_tool = lambda: {'function': {'name': 'cmd-run'}}

    # tool_call with valid command but invalid timeout
    tc = DummyToolCall(id='t1', name='cmd-run', arguments=json.dumps({'command': 'echo', 'timeout': 'bad_float'}))
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp1', choices=[DummyChoice(msg)])

    with pytest.raises(fc.FunctionCallValidationError) as e:
        fc.response_to_actions(resp)
    assert 'Invalid float passed to' in str(e.value)


def test_cmd_run_success_thought_list_round_020():
    """CmdRunAction constructed, timeout applied, and thought from content list combined into first action."""
    fc.create_cmd_run_tool = lambda: {'function': {'name': 'cmd-run'}}

    # content is list with text messages -> thought concatenation path
    content_list = [{'type': 'text', 'text': 'hello '}, {'type': 'text', 'text': 'world'}]
    tc = DummyToolCall(id='t2', name='cmd-run', arguments=json.dumps({'command': 'ls', 'is_input': 'true', 'timeout': '2.5'}))
    msg = DummyChoiceMessage(content=content_list, tool_calls=[tc])
    resp = DummyModelResponse(id='resp2', choices=[DummyChoice(msg)])

    actions = fc.response_to_actions(resp)
    # should produce a single DummyCmdRunAction
    assert len(actions) == 1
    a = actions[0]
    assert isinstance(a, DummyCmdRunAction)
    assert a.command == 'ls'
    assert a.is_input is True
    # timeout applied via set_hard_timeout
    assert a._timeout == pytest.approx(2.5)
    # combine_thought should have set 'thought'
    assert getattr(a, 'thought') == 'hello world'
    # metadata and response id should be set
    assert a.tool_call_metadata.function_name == 'cmd-run'
    assert a.response_id == 'resp2'


def test_task_tracking_normalization_round_020():
    """Task tracking normalizes tasks with default fields when valid list provided."""
    fc.TASK_TRACKER_TOOL_NAME = 'task-tracker'

    raw_task = {'title': 'My Task'}  # missing id, status, notes
    args = {'command': 'add', 'task_list': [raw_task]}
    tc = DummyToolCall(id='t3', name='task-tracker', arguments=json.dumps(args))
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp3', choices=[DummyChoice(msg)])

    actions = fc.response_to_actions(resp)
    assert len(actions) == 1
    a = actions[0]
    assert isinstance(a, DummyTaskTrackingAction)
    assert a.command == 'add'
    # normalized task should have defaults applied
    assert isinstance(a.task_list, list) and len(a.task_list) == 1
    nt = a.task_list[0]
    assert nt['title'] == 'My Task'
    assert nt['id'].startswith('task-')
    assert nt['status'] == 'todo'
    assert nt['notes'] == ''


def test_task_tracking_missing_command_errors_round_020():
    """Missing 'command' in task tracker should raise validation error."""
    fc.TASK_TRACKER_TOOL_NAME = 'task-tracker'

    tc = DummyToolCall(id='t4', name='task-tracker', arguments=json.dumps({}))
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp4', choices=[DummyChoice(msg)])

    with pytest.raises(fc.FunctionCallValidationError):
        fc.response_to_actions(resp)


def test_mcp_action_round_020():
    """When mcp_tool_names contains a tool name, an MCPAction is created with provided arguments."""
    # tool name recognized as MCP tool
    tool_name = 'my_mcp_tool'
    tc = DummyToolCall(id='t5', name=tool_name, arguments=json.dumps({'a': 1}))
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp5', choices=[DummyChoice(msg)])

    actions = fc.response_to_actions(resp, mcp_tool_names=[tool_name])
    assert len(actions) == 1
    a = actions[0]
    assert isinstance(a, DummyMCPAction)
    assert a.name == tool_name
    assert a.arguments == {'a': 1}
    assert a.response_id == 'resp5'


def test_json_parse_error_round_020():
    """Invalid JSON in function.arguments should raise FunctionCallValidationError."""
    fc.create_cmd_run_tool = lambda: {'function': {'name': 'cmd-run'}}
    tc = DummyToolCall(id='t6', name='cmd-run', arguments='not-a-json')
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp6', choices=[DummyChoice(msg)])

    with pytest.raises(fc.FunctionCallValidationError) as e:
        fc.response_to_actions(resp)
    assert 'Failed to parse tool call arguments' in str(e.value)


def test_unregistered_tool_round_020():
    """If a tool name is not registered and not in mcp_tool_names, FunctionCallNotExistsError is raised."""
    tc = DummyToolCall(id='t7', name='unknown_tool', arguments=json.dumps({'x': 1}))
    msg = DummyChoiceMessage(content=None, tool_calls=[tc])
    resp = DummyModelResponse(id='resp7', choices=[DummyChoice(msg)])

    with pytest.raises(fc.FunctionCallNotExistsError):
        fc.response_to_actions(resp)
