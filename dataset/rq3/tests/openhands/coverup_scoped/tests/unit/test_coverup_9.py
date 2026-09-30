# file: openhands/runtime/base.py:1033-1120
# asked: {"lines": [1038, 1039, 1040, 1041, 1043, 1044, 1046, 1048, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1059, 1060, 1061, 1062, 1063, 1064, 1066, 1067, 1068, 1071, 1073, 1074, 1075, 1076, 1077, 1078, 1080, 1081, 1082, 1083, 1084, 1086, 1087, 1088, 1089, 1090, 1093, 1094, 1095, 1096, 1098, 1100, 1101, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1113, 1116, 1117, 1119, 1120], "branches": [[1038, 1039], [1038, 1099], [1039, 1040], [1039, 1041], [1041, 1043], [1041, 1098], [1048, 1050], [1048, 1071], [1051, 1052], [1051, 1059], [1071, 1073], [1071, 1093], [1099, 1104], [1099, 1105], [1106, 1107], [1106, 1108], [1108, 1109], [1108, 1112], [1112, 1116], [1112, 1119]]}
# gained: {"lines": [1038, 1039, 1040, 1041, 1043, 1044, 1046, 1048, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1059, 1060, 1061, 1062, 1063, 1064, 1066, 1067, 1068, 1071, 1073, 1074, 1075, 1076, 1077, 1078, 1080, 1081, 1082, 1083, 1084, 1086, 1087, 1088, 1089, 1090, 1093, 1094, 1095, 1096, 1098, 1100, 1101, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1113, 1116, 1117, 1119, 1120], "branches": [[1038, 1039], [1038, 1099], [1039, 1040], [1039, 1041], [1041, 1043], [1041, 1098], [1048, 1050], [1048, 1071], [1051, 1052], [1051, 1059], [1071, 1073], [1071, 1093], [1099, 1104], [1099, 1105], [1106, 1107], [1106, 1108], [1108, 1109], [1108, 1112], [1112, 1116], [1112, 1119]]}

import pytest
from types import SimpleNamespace

from openhands.runtime.base import Runtime
import openhands.runtime.base as base_mod
from openhands.events.action.agent import AgentThinkAction, TaskTrackingAction
from openhands.events.action.action import ActionConfirmationStatus
from openhands.events.observation.error import ErrorObservation
from openhands.events.observation.empty import NullObservation
from openhands.events.observation.task_tracking import TaskTrackingObservation
from openhands.events.observation.agent import AgentThinkObservation
from openhands.events.observation.reject import UserRejectObservation
from openhands.events.serialization.action import ACTION_TYPE_TO_CLASS


class DummyFileStore:
    def __init__(self, reads=None, write_side_effect=None, read_side_effect=None):
        self.written = {}
        self.reads = reads or {}
        self._write_side_effect = write_side_effect
        self._read_side_effect = read_side_effect

    def write(self, path, content):
        if self._write_side_effect:
            raise self._write_side_effect
        self.written[path] = content

    def read(self, path):
        if self._read_side_effect:
            raise self._read_side_effect
        if path in self.reads:
            return self.reads[path]
        raise FileNotFoundError(path)


class DummyEventStream:
    def __init__(self, user_id='user-1', file_store=None):
        self.user_id = user_id
        self.file_store = file_store or DummyFileStore()

    def subscribe(self, *a, **k):
        # minimal stub for tests
        return None


class DummyRuntime(Runtime):
    """Concrete runtime implementing abstract methods minimally for testing."""
    def __init__(self):
        # Do NOT call super().__init__; provide minimal attributes used by run_action
        self.sid = 'session-123'
        self.event_stream = DummyEventStream()
        # Other attributes to satisfy potential usage
        self.user_id = self.event_stream.user_id

    # Implement required abstract methods with minimal behavior
    def browse(self, *a, **k):
        return NullObservation('')

    def browse_interactive(self, *a, **k):
        return NullObservation('')

    async def call_tool_mcp(self, *a, **k):
        return NullObservation('')

    async def connect(self, *a, **k):
        return None

    def copy_from(self, *a, **k):
        return None

    def copy_to(self, *a, **k):
        return None

    def edit(self, *a, **k):
        return NullObservation('')

    def get_mcp_config(self, *a, **k):
        return {}

    def list_files(self, *a, **k):
        return []

    def read(self, *a, **k):
        return NullObservation('')

    def run(self, *a, **k):
        return NullObservation('')

    def run_ipython(self, *a, **k):
        return NullObservation('')

    def write(self, *a, **k):
        return NullObservation('')


def make_runtime():
    rt = DummyRuntime()
    rt.sid = 'session-123'
    rt.event_stream = DummyEventStream()
    return rt


def make_action_obj(**kwargs):
    return SimpleNamespace(**kwargs)


def test_agent_think_returns_agent_think_observation(monkeypatch):
    rt = make_runtime()
    monkeypatch.setattr(base_mod, "get_conversation_dir", lambda sid, uid: "/tmp/session/", raising=False)

    action = AgentThinkAction(thought="I think", action=AgentThinkAction.action)
    obs = rt.run_action(action)
    assert isinstance(obs, AgentThinkObservation)
    assert hasattr(obs, "observation")


def test_task_tracking_plan_success_and_write_failure(monkeypatch):
    rt = make_runtime()
    monkeypatch.setattr(base_mod, "get_conversation_dir", lambda sid, uid: "/tmp/session/", raising=False)

    # Success case
    file_store = DummyFileStore()
    rt.event_stream.file_store = file_store

    tasks = [
        {"title": "Task A", "notes": "Notes A", "status": "todo"},
        {"title": "Task B", "notes": "Notes B", "status": "done"},
    ]
    action_plan = TaskTrackingAction(command="plan", task_list=tasks)
    obs = rt.run_action(action_plan)
    assert isinstance(obs, TaskTrackingObservation)
    expected_path = f"/tmp/session/TASKS.md"
    assert expected_path in file_store.written
    written_content = file_store.written[expected_path]
    assert "# Task List" in written_content
    assert "1." in written_content and "2." in written_content
    assert str(len(tasks)) in obs.content or "Task list has been updated" in obs.content

    # Failure case: write raises
    file_store_fail = DummyFileStore(write_side_effect=Exception("disk full"))
    rt.event_stream.file_store = file_store_fail
    action_plan2 = TaskTrackingAction(command="plan", task_list=tasks)
    obs2 = rt.run_action(action_plan2)
    assert isinstance(obs2, ErrorObservation)
    assert "Failed to write task list" in obs2.message or "disk full" in str(obs2)


def test_task_tracking_view_variants(monkeypatch):
    rt = make_runtime()
    monkeypatch.setattr(base_mod, "get_conversation_dir", lambda sid, uid: "/tmp/session/", raising=False)
    expected_path = f"/tmp/session/TASKS.md"

    # view success
    file_store = DummyFileStore(reads={expected_path: "CURRENT TASKS CONTENT"})
    rt.event_stream.file_store = file_store
    action_view = TaskTrackingAction(command="view")
    obs = rt.run_action(action_view)
    assert isinstance(obs, TaskTrackingObservation)
    assert obs.content == "CURRENT TASKS CONTENT"

    # view FileNotFoundError -> message about creating one
    file_store_missing = DummyFileStore()
    rt.event_stream.file_store = file_store_missing
    obs_missing = rt.run_action(TaskTrackingAction(command="view"))
    assert isinstance(obs_missing, TaskTrackingObservation)
    assert "No task list found" in obs_missing.content

    # view other exception
    file_store_bad = DummyFileStore(read_side_effect=Exception("read failure"))
    rt.event_stream.file_store = file_store_bad
    obs_err = rt.run_action(TaskTrackingAction(command="view"))
    assert isinstance(obs_err, TaskTrackingObservation)
    assert "Failed to read the task list" in obs_err.content


def test_task_tracking_unknown_command_returns_message(monkeypatch):
    rt = make_runtime()
    monkeypatch.setattr(base_mod, "get_conversation_dir", lambda sid, uid: "/tmp/session/", raising=False)
    rt.event_stream.file_store = DummyFileStore()
    action_unknown = TaskTrackingAction(command="unknowncmd")
    obs = rt.run_action(action_unknown)
    assert isinstance(obs, TaskTrackingObservation)
    assert "Unknown command: unknowncmd" in obs.content


def test_non_runnable_other_action_returns_null():
    rt = make_runtime()
    fake_action = make_action_obj(runnable=False)
    obs = rt.run_action(fake_action)
    assert isinstance(obs, NullObservation)


def test_runnable_awaiting_confirmation_returns_null():
    rt = make_runtime()
    fake_action = make_action_obj(runnable=True, confirmation_state=ActionConfirmationStatus.AWAITING_CONFIRMATION)
    obs = rt.run_action(fake_action)
    assert isinstance(obs, NullObservation)


def test_action_type_not_exist_and_not_supported():
    rt = make_runtime()
    fake_action = make_action_obj(runnable=True, action="completely_nonexistent_action")
    obs = rt.run_action(fake_action)
    assert isinstance(obs, ErrorObservation)
    assert "does not exist" in obs.message

    if len(ACTION_TYPE_TO_CLASS) == 0:
        pytest.skip("No actions registered in ACTION_TYPE_TO_CLASS")
    some_action_type = next(iter(ACTION_TYPE_TO_CLASS.keys()))
    fake_action2 = make_action_obj(runnable=True, action=some_action_type)
    if hasattr(rt, some_action_type):
        pytest.skip(f"Runtime already has attribute {some_action_type}; skipping unsupported-action check")
    obs2 = rt.run_action(fake_action2)
    assert isinstance(obs2, ErrorObservation)
    assert "not supported in the current runtime" in obs2.message


def test_action_rejected_and_execute_success():
    rt = make_runtime()
    if len(ACTION_TYPE_TO_CLASS) == 0:
        pytest.skip("No actions registered")
    some_action_type = next(iter(ACTION_TYPE_TO_CLASS.keys()))

    def impl_returning_observation(action):
        return AgentThinkObservation("done")

    if not some_action_type.isidentifier():
        pytest.skip(f"Action type name {some_action_type!r} is not a valid identifier for setattr/getattr")

    setattr(rt, some_action_type, impl_returning_observation)

    fake_rejected = make_action_obj(runnable=True, action=some_action_type, confirmation_state=ActionConfirmationStatus.REJECTED)
    obs_rej = rt.run_action(fake_rejected)
    assert isinstance(obs_rej, UserRejectObservation)

    fake_exec = make_action_obj(runnable=True, action=some_action_type)
    obs_exec = rt.run_action(fake_exec)
    assert isinstance(obs_exec, AgentThinkObservation)
    assert hasattr(obs_exec, "observation")
