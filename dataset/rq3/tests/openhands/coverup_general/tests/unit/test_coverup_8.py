# file: openhands/security/grayswan/utils.py:30-152
# asked: {"lines": [32, 34, 36, 37, 40, 47, 50, 51, 52, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 68, 69, 70, 71, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 96, 97, 99, 100, 101, 102, 103, 104, 105, 107, 109, 110, 111, 112, 115, 118, 119, 120, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 146, 148, 149, 152], "branches": [[36, 37], [36, 152], [40, 47], [40, 50], [50, 51], [50, 54], [54, 55], [54, 67], [56, 57], [56, 61], [61, 36], [61, 62], [67, 74], [67, 118], [78, 36], [78, 79], [83, 36], [83, 84], [85, 86], [85, 109], [86, 87], [86, 107], [100, 101], [100, 102], [118, 36], [118, 132], [133, 134], [133, 136], [137, 138], [137, 140], [140, 141], [140, 148]]}
# gained: {"lines": [32, 34, 36, 37, 40, 47, 50, 51, 52, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 68, 69, 70, 71, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 96, 97, 99, 100, 101, 102, 103, 104, 105, 107, 109, 110, 111, 112, 115, 118, 119, 120, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 146, 148, 149, 152], "branches": [[36, 37], [36, 152], [40, 47], [40, 50], [50, 51], [50, 54], [54, 55], [54, 67], [56, 57], [56, 61], [61, 62], [67, 74], [67, 118], [78, 79], [83, 84], [85, 86], [85, 109], [86, 87], [86, 107], [100, 101], [118, 132], [133, 134], [133, 136], [137, 138], [137, 140], [140, 141], [140, 148]]}

import json
import types
import pytest
import importlib

# Import the module under test
utils = importlib.import_module("openhands.security.grayswan.utils")


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


class DummyEventSource:
    USER = "user"
    AGENT = "agent"
    ENVIRONMENT = "environment"


# Dummy classes to stand in for the various action/observation classes.
class DummySystemMessageAction:
    def __init__(self, content):
        self.content = content


class DummyMessageAction:
    def __init__(self, content, source=None, source_attr_name="_source"):
        self.content = content
        # some code uses _source, some uses source
        if source_attr_name == "_source":
            if source is not None:
                self._source = source
        else:
            if source is not None:
                self.source = source


class DummyObservation:
    pass


# Observation subclasses (so isinstance checks behave)
class DummyFileReadObservation(DummyObservation):
    def __init__(self, content=None, source=None, tool_call_metadata=None):
        if content is not None:
            self.content = content
        if source is not None:
            self._source = source
        if tool_call_metadata is not None:
            self.tool_call_metadata = tool_call_metadata


class DummyFileWriteObservation(DummyFileReadObservation):
    pass


class DummyFileEditObservation(DummyFileReadObservation):
    pass


class DummyCmdOutputObservation(DummyFileReadObservation):
    pass


class DummyIPythonRunCellObservation(DummyFileReadObservation):
    pass


class DummyBrowserOutputObservation(DummyFileReadObservation):
    pass


class DummyMCPObservation(DummyFileReadObservation):
    pass


class DummyFileDownloadObservation(DummyFileReadObservation):
    pass


def make_tool_call_with_id(id_value, func_name, func_arguments):
    class FuncObj:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class ToolCallObj:
        def __init__(self, id_, function, type_="function"):
            self.id = id_
            self.function = function
            self.type = type_

    return ToolCallObj(id_value, FuncObj(func_name, func_arguments))


class DummyToolMetadata:
    def __init__(self, model_response=None, tool_call_id=None):
        self.model_response = model_response
        self.tool_call_id = tool_call_id


class DummyToolEvent:
    """An event that is NOT an Observation, but has tool_call_metadata and a source."""

    def __init__(self, tool_call_metadata, source):
        self.tool_call_metadata = tool_call_metadata
        self._source = source


@pytest.fixture(autouse=True)
def patch_utils(monkeypatch):
    """
    Monkeypatch the utils module to use dummy classes and a capturable logger.
    This fixture is autouse so every test gets a clean patched environment.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr(utils, "openhands_logger", dummy_logger, raising=False)
    # The module references `logger` name bound at import time; replace that attribute
    monkeypatch.setattr(utils, "logger", dummy_logger, raising=True)

    # Patch EventSource
    monkeypatch.setattr(utils, "EventSource", DummyEventSource, raising=True)

    # Patch action/observation classes used in isinstance checks
    monkeypatch.setattr(utils, "SystemMessageAction", DummySystemMessageAction, raising=True)
    monkeypatch.setattr(utils, "MessageAction", DummyMessageAction, raising=True)

    # Patch Observation base and concrete observation classes
    monkeypatch.setattr(utils, "Observation", DummyObservation, raising=True)
    monkeypatch.setattr(utils, "FileReadObservation", DummyFileReadObservation, raising=True)
    monkeypatch.setattr(utils, "FileWriteObservation", DummyFileWriteObservation, raising=True)
    monkeypatch.setattr(utils, "FileEditObservation", DummyFileEditObservation, raising=True)
    monkeypatch.setattr(utils, "CmdOutputObservation", DummyCmdOutputObservation, raising=True)
    monkeypatch.setattr(utils, "IPythonRunCellObservation", DummyIPythonRunCellObservation, raising=True)
    monkeypatch.setattr(utils, "BrowserOutputObservation", DummyBrowserOutputObservation, raising=True)
    monkeypatch.setattr(utils, "MCPObservation", DummyMCPObservation, raising=True)
    monkeypatch.setattr(utils, "FileDownloadObservation", DummyFileDownloadObservation, raising=True)

    yield
    # monkeypatch will automatically undo changes after test


def test_skip_agent_state_changed_and_internal_types():
    # Create an object whose type name is one of the names intended to be skipped.
    SkipType = type("AgentStateChangedObservation", (), {})
    events = [SkipType()]
    msgs = utils.convert_events_to_openai_messages(events)
    # Should skip and produce empty list
    assert msgs == []
    # logger.info should have been called and recorded
    assert any("Converting 1 events" in s for s in utils.logger.infos)


def test_system_and_message_actions_user_and_agent():
    # System message should be converted to system role
    sys_evt = DummySystemMessageAction("system content")
    # MessageAction as user (use attribute name _source)
    user_evt = DummyMessageAction("hello user", source=DummyEventSource.USER)
    # MessageAction as agent (use attribute name 'source' to exercise getattr path)
    agent_evt = DummyMessageAction("hello agent", source=DummyEventSource.AGENT, source_attr_name="source")
    events = [sys_evt, user_evt, agent_evt]
    msgs = utils.convert_events_to_openai_messages(events)
    # Expect three messages in order: system, user, assistant
    assert msgs[0] == {"role": "system", "content": "system content"}
    assert msgs[1] == {"role": "user", "content": "hello user"}
    assert msgs[2] == {"role": "assistant", "content": "hello agent"}


def test_tool_calls_serialization_and_json_handling():
    # Create a tool call with valid JSON arguments containing 'security_risk' to be removed
    args_with_risk = {"a": 1, "security_risk": "yes", "b": 2}
    tc1 = make_tool_call_with_id("tc1", "do_something", json.dumps(args_with_risk))

    # Create a tool call with invalid JSON to trigger JSONDecodeError branch
    tc2 = make_tool_call_with_id("tc2", "do_other", "not a json string")

    # Create a plain dict tool call without 'id' to be appended as-is
    tc3 = {"not_an_object": True, "some": "value"}

    message_data = {
        "content": "assistant used tools",
        "tool_calls": [tc1, tc2, tc3],
    }
    choice = {"message": message_data}
    model_response = {"choices": [choice]}

    tool_meta = DummyToolMetadata(model_response=model_response)
    evt = DummyToolEvent(tool_call_metadata=tool_meta, source=DummyEventSource.AGENT)

    msgs = utils.convert_events_to_openai_messages([evt])

    # Should produce one assistant message with tool_calls
    assert len(msgs) == 1
    assistant_msg = msgs[0]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "assistant used tools"
    # tool_calls should be a list of three entries
    tcs = assistant_msg["tool_calls"]
    assert len(tcs) == 3
    # First should be a dict with id and function.arguments being JSON string without security_risk
    first = tcs[0]
    assert first["id"] == "tc1"
    parsed_args = json.loads(first["function"]["arguments"])
    assert "security_risk" not in parsed_args
    assert parsed_args["a"] == 1 and parsed_args["b"] == 2
    # Second had invalid JSON: it should still be present and arguments remain unchanged string
    second = tcs[1]
    assert second["id"] == "tc2"
    # Arguments should still be the original invalid string or preserved as-is
    assert second["function"]["arguments"] == "not a json string"
    # Third appended as-is (a dict)
    assert tcs[2] is tc3


def test_observation_tool_responses_and_warnings(monkeypatch):
    # Observation from environment should be skipped even if has tool_call_id
    meta_with_id = DummyToolMetadata(tool_call_id="call123")
    env_obs = DummyFileReadObservation(content="env content", source=DummyEventSource.ENVIRONMENT, tool_call_metadata=meta_with_id)

    # Observation with tool_call_id should produce a tool role message
    obs_with_id = DummyFileReadObservation(content="file contents", source=DummyEventSource.AGENT, tool_call_metadata=meta_with_id)

    # Observation without tool_call_metadata (or with falsy) should trigger a warning
    obs_no_meta = DummyFileReadObservation(content="no meta", source=DummyEventSource.AGENT)

    # Capture logger warnings by using the patched logger
    msgs = utils.convert_events_to_openai_messages([env_obs, obs_with_id, obs_no_meta])

    # env_obs skipped, obs_with_id should have produced one tool message
    tool_msgs = [m for m in msgs if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    tm = tool_msgs[0]
    assert tm["content"] == "file contents"
    assert tm["tool_call_id"] == "call123"

    # There should be a warning logged for obs_no_meta missing tool_call_id
    assert any("Could not find tool_call_id for observation" in w for w in utils.logger.warnings)
