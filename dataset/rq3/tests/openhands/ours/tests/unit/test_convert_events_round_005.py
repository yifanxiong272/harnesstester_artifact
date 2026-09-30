import importlib
import json
import types
import pytest


def test_convert_events_to_openai_messages_round_005(monkeypatch):
    """Exercise multiple branches of convert_events_to_openai_messages.

    This test patches the names the utility expects from the openhands
    package into the module under test, constructs a mixture of events
    including system/user/agent messages, a tool call with a tool call
    metadata that contains a model_response with tool_calls (including
    a ToolCall whose function.arguments JSON contains a 'security_risk'
    key), and observations both with and without a tool_call_id.

    Assertions verify:
    - system/user/assistant messages are produced
    - a tool-call-derived assistant message is produced
    - security_risk was removed from the serialized arguments
    - an observation with a tool_call_id yields a 'tool' role message
    - an observation without a tool_call_id triggers a logger.warning
    """
    # Import the module under test
    utils = importlib.import_module("openhands.security.grayswan.utils")

    # Provide a lightweight EventSource replacement used by the code under test
    class EventSource:
        USER = "user"
        AGENT = "agent"
        ENVIRONMENT = "environment"

    monkeypatch.setattr(utils, "EventSource", EventSource, raising=False)

    # A fake logger that records calls for later assertions
    logs = {"infos": [], "warnings": []}

    class FakeLogger:
        def info(self, msg):
            logs["infos"].append(msg)

        def warning(self, msg):
            logs["warnings"].append(msg)

    monkeypatch.setattr(utils, "logger", FakeLogger(), raising=False)

    # Observation base and concrete observation types (the real code does isinstance checks)
    class Observation:
        pass

    monkeypatch.setattr(utils, "Observation", Observation, raising=False)

    # Create the observation subclasses referenced in the implementation
    class FileReadObservation(Observation):
        pass

    class FileWriteObservation(Observation):
        pass

    class FileEditObservation(Observation):
        pass

    class CmdOutputObservation(Observation):
        pass

    class IPythonRunCellObservation(Observation):
        pass

    class BrowserOutputObservation(Observation):
        pass

    class MCPObservation(Observation):
        pass

    class FileDownloadObservation(Observation):
        pass

    for name, cls in (
        ("FileReadObservation", FileReadObservation),
        ("FileWriteObservation", FileWriteObservation),
        ("FileEditObservation", FileEditObservation),
        ("CmdOutputObservation", CmdOutputObservation),
        ("IPythonRunCellObservation", IPythonRunCellObservation),
        ("BrowserOutputObservation", BrowserOutputObservation),
        ("MCPObservation", MCPObservation),
        ("FileDownloadObservation", FileDownloadObservation),
    ):
        monkeypatch.setattr(utils, name, cls, raising=False)

    # Define lightweight action/message classes used for isinstance checks
    class MessageAction:
        def __init__(self, content, source=None, _source=None):
            self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source

    class SystemMessageAction:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr(utils, "MessageAction", MessageAction, raising=False)
    monkeypatch.setattr(utils, "SystemMessageAction", SystemMessageAction, raising=False)

    # Tool call representation: a minimal object with the attributes the code reads
    class ToolFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class ToolCall:
        def __init__(self, id, type, function):
            self.id = id
            self.type = type
            self.function = function

    class ToolCallMetadata:
        def __init__(self, model_response=None, tool_call_id=None):
            self.model_response = model_response
            self.tool_call_id = tool_call_id

    # Build an event carrying tool_call_metadata with choices -> message -> tool_calls
    # The first tool call has an arguments JSON that includes 'security_risk' to be removed
    function_args_with_risk = json.dumps({"value": 1, "security_risk": True})
    tc_obj = ToolCall(id="tc-id-1", type="function", function=ToolFunction("do_stuff", function_args_with_risk))
    # A second tool call that does not have an 'id' attribute (will hit the else branch and be appended as-is)
    tc_no_id = {"not": "an object with id"}

    model_response = {"choices": [{"message": {"content": "assistant-with-tool", "tool_calls": [tc_obj, tc_no_id]}}]}
    tool_meta = ToolCallMetadata(model_response=model_response)

    class GenericEvent:
        pass

    tool_event = GenericEvent()
    tool_event.tool_call_metadata = tool_meta
    # Mark it as coming from the agent (so the tool-call branch applies)
    tool_event._source = EventSource.AGENT

    # Observation that includes tool_call_metadata with a tool_call_id -> should produce a 'tool' message
    obs_with_id = FileReadObservation()
    obs_with_id.content = "file content here"
    obs_with_id.tool_call_metadata = types.SimpleNamespace(tool_call_id="tc-id-1")
    obs_with_id._source = EventSource.USER

    # Observation without tool_call_id -> should trigger logger.warning
    obs_without_id = FileWriteObservation()
    obs_without_id.content = "write content"
    obs_without_id._source = EventSource.USER

    # An event type that should be skipped based on its type name
    class AgentStateChangedObservation:
        pass

    skip_event = AgentStateChangedObservation()

    # System / user / agent messages
    sys_msg = SystemMessageAction("system-level instruction")
    user_msg = MessageAction("hello user", _source=EventSource.USER)
    agent_msg = MessageAction("agent reply", source=EventSource.AGENT)

    events = [skip_event, sys_msg, user_msg, agent_msg, tool_event, obs_with_id, obs_without_id]

    result = utils.convert_events_to_openai_messages(events)

    # Expect: system, user, assistant(from agent_msg), assistant (from tool_event with tool_calls), tool (from obs_with_id)
    # The skip_event and obs_without_id should not produce messages (obs_without_id produces only a warning)
    # Assert count and key features
    assert isinstance(result, list)
    # There should be 5 messages produced as described above
    assert len(result) == 5

    # System message check
    assert result[0]["role"] == "system" and result[0]["content"] == "system-level instruction"

    # User message present
    assert any(m.get("role") == "user" and m.get("content") == "hello user" for m in result)

    # Assistant reply from agent_msg present
    assert any(m.get("role") == "assistant" and m.get("content") == "agent reply" for m in result)

    # There must be an assistant message that contains tool_calls
    assistant_tool_messages = [m for m in result if m.get("role") == "assistant" and m.get("tool_calls") is not None]
    assert len(assistant_tool_messages) == 1
    assistant_tool_msg = assistant_tool_messages[0]

    # The first tool_call entry should be converted to a dict with function.arguments as a JSON string
    first_tc = assistant_tool_msg["tool_calls"][0]
    assert isinstance(first_tc, dict)
    assert first_tc["id"] == "tc-id-1"
    assert "function" in first_tc and "arguments" in first_tc["function"]

    # Ensure 'security_risk' was removed from the arguments JSON string
    parsed_args = json.loads(first_tc["function"]["arguments"])
    assert "security_risk" not in parsed_args

    # Observation produced 'tool' role message with expected fields
    tool_msgs = [m for m in result if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["content"] == "file content here" and tool_msgs[0]["tool_call_id"] == "tc-id-1"

    # Confirm that a warning was recorded for the observation without a tool_call_id
    assert logs["warnings"], "Expected a warning recorded for an observation missing tool_call_id"
