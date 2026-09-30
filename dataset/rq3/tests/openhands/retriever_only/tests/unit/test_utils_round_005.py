import types
from types import SimpleNamespace
import pytest

from openhands.security.grayswan import utils
from openhands.security.grayswan.utils import convert_events_to_openai_messages


class DummyEventSource:
    USER = "USER"
    AGENT = "AGENT"
    ENVIRONMENT = "ENVIRONMENT"


def _install_dummy_classes(monkeypatch):
    """Monkeypatch the utils module symbols used by convert_events_to_openai_messages
    to lightweight test doubles so we can precisely control behavior."""
    # Base Observation class and its specific observation subclasses
    class DummyObservation:
        pass

    class FileReadObservation(DummyObservation):
        pass

    class FileWriteObservation(DummyObservation):
        pass

    class FileEditObservation(DummyObservation):
        pass

    class CmdOutputObservation(DummyObservation):
        pass

    class IPythonRunCellObservation(DummyObservation):
        pass

    class BrowserOutputObservation(DummyObservation):
        pass

    class MCPObservation(DummyObservation):
        pass

    class FileDownloadObservation(DummyObservation):
        pass

    # Message and system actions
    class SystemMessageAction:
        def __init__(self, content):
            self.content = content

    class MessageAction:
        def __init__(self, content, _source=None, source=None):
            self.content = content
            if _source is not None:
                self._source = _source
            if source is not None:
                self.source = source

    # Install into module
    monkeypatch.setattr(utils, "EventSource", DummyEventSource)
    monkeypatch.setattr(utils, "Observation", DummyObservation)
    monkeypatch.setattr(utils, "FileReadObservation", FileReadObservation)
    monkeypatch.setattr(utils, "FileWriteObservation", FileWriteObservation)
    monkeypatch.setattr(utils, "FileEditObservation", FileEditObservation)
    monkeypatch.setattr(utils, "CmdOutputObservation", CmdOutputObservation)
    monkeypatch.setattr(utils, "IPythonRunCellObservation", IPythonRunCellObservation)
    monkeypatch.setattr(utils, "BrowserOutputObservation", BrowserOutputObservation)
    monkeypatch.setattr(utils, "MCPObservation", MCPObservation)
    monkeypatch.setattr(utils, "FileDownloadObservation", FileDownloadObservation)
    monkeypatch.setattr(utils, "SystemMessageAction", SystemMessageAction)
    monkeypatch.setattr(utils, "MessageAction", MessageAction)


def test_system_and_messages_round_005(monkeypatch):
    # Arrange: install dummy classes
    _install_dummy_classes(monkeypatch)

    # Create events: system message, user message, agent message
    sys_evt = utils.SystemMessageAction("system-configuration")
    user_evt = utils.MessageAction("hello-user", _source=utils.EventSource.USER)
    agent_evt = utils.MessageAction("reply-agent", _source=utils.EventSource.AGENT)

    # Act
    out = convert_events_to_openai_messages([sys_evt, user_evt, agent_evt])

    # Assert: roles and contents are preserved and in order
    assert isinstance(out, list)
    assert len(out) == 3
    assert out[0] == {"role": "system", "content": "system-configuration"}
    assert out[1]["role"] == "user" and out[1]["content"] == "hello-user"
    assert out[2]["role"] == "assistant" and out[2]["content"] == "reply-agent"


def test_tool_calls_with_security_risk_and_no_id_round_005(monkeypatch):
    # Arrange: install dummy classes
    _install_dummy_classes(monkeypatch)

    # Tool call that has id and function.arguments JSON containing security_risk
    class FunctionWithArgs:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class ToolCallWithId:
        def __init__(self):
            self.id = "tc-1"
            self.type = "function"
            self.function = FunctionWithArgs("do_something", '{"x": 1, "security_risk": true}')

    # Tool call without id: should go through else branch and be appended as-is
    class ToolCallNoId:
        def __init__(self):
            self.type = "function"
            self.function = FunctionWithArgs("other", '{"y": 2}')

    tc1 = ToolCallWithId()
    tc2 = ToolCallNoId()

    # tool_call_metadata contains model_response structure expected by function
    tool_metadata = SimpleNamespace(model_response={
        "choices": [
            {"message": {"content": "assistant-content", "tool_calls": [tc1, tc2]}}
        ]
    })

    # Event that is NOT an Observation and has tool_call_metadata and is from AGENT
    class AgentToolEvent:
        def __init__(self, tool_call_metadata):
            self.tool_call_metadata = tool_call_metadata
            self._source = utils.EventSource.AGENT

    evt = AgentToolEvent(tool_metadata)

    # Act
    out = convert_events_to_openai_messages([evt])

    # Assert: one assistant message created
    assert len(out) == 1
    assistant_msg = out[0]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "assistant-content"
    # First tool_call should be a dict with id and its function.arguments JSON should NOT contain security_risk
    tc_list = assistant_msg["tool_calls"]
    assert isinstance(tc_list, list) and len(tc_list) == 2
    first = tc_list[0]
    assert first["id"] == "tc-1"
    assert "security_risk" not in first["function"]["arguments"]
    # Second entry should have been appended as the original object (not converted to dict)
    second = tc_list[1]
    # We expect the original object (ToolCallNoId) to be present
    assert hasattr(second, "function") and getattr(second.function, "name") == "other"


def test_tool_call_json_decode_error_and_observations_round_005(monkeypatch, caplog):
    # Arrange: install dummy classes
    _install_dummy_classes(monkeypatch)

    # Tool call where function.arguments is invalid JSON -> triggers except path
    class FunctionBadArgs:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class ToolCallBadJSON:
        def __init__(self):
            self.id = "tc-bad"
            self.type = "function"
            # invalid JSON to trigger JSONDecodeError
            self.function = FunctionBadArgs("broken", "{not: valid}")

    tc_bad = ToolCallBadJSON()
    tool_metadata_bad = SimpleNamespace(model_response={
        "choices": [
            {"message": {"content": "assist-bad", "tool_calls": [tc_bad]}}
        ]
    })

    class AgentToolEventBad:
        def __init__(self, tool_call_metadata):
            self.tool_call_metadata = tool_call_metadata
            self._source = utils.EventSource.AGENT

    evt_bad = AgentToolEventBad(tool_metadata_bad)

    # Also test observation handling: one observation with ENVIRONMENT source should be skipped
    class SomeFileRead(utils.FileReadObservation):
        def __init__(self, content, tool_call_metadata=None, source=None, _source=None):
            self.content = content
            self.tool_call_metadata = tool_call_metadata
            if _source is not None:
                self._source = _source
            if source is not None:
                self.source = source

    # Observation from ENVIRONMENT should be skipped
    obs_env = SomeFileRead("ignored-content", _source=utils.EventSource.ENVIRONMENT)

    # Observation with a tool_call_id should produce a tool message
    meta_with_id = SimpleNamespace(tool_call_id="tool-call-xyz")
    obs_with_id = SomeFileRead("file-contents", tool_call_metadata=meta_with_id, _source=utils.EventSource.USER)

    # Act
    caplog.clear()
    out = convert_events_to_openai_messages([evt_bad, obs_env, obs_with_id])

    # Assert: first entry from tool_calls (bad JSON) still results in assistant message; arguments unchanged
    # and observation with tool_call_id produced a tool message; observation with ENVIRONMENT was skipped
    # We expect two messages: assistant (from tool_calls) and tool (from obs_with_id)
    roles = [m.get("role") for m in out]
    assert "assistant" in roles
    assert "tool" in roles

    # Find assistant message and assert the function.arguments remains the invalid string (exception path)
    assistant = next(m for m in out if m.get("role") == "assistant")
    tc_first = assistant["tool_calls"][0]
    assert tc_first["id"] == "tc-bad"
    assert tc_first["function"]["arguments"] == "{not: valid}"

    # Find tool message and assert tool_call_id and content are present
    tool_msg = next(m for m in out if m.get("role") == "tool")
    assert tool_msg["tool_call_id"] == "tool-call-xyz"
    assert tool_msg["content"] == "file-contents"

    # Ensure that the ENVIRONMENT observation produced no message (we had only two messages)
    assert len(out) == 2
