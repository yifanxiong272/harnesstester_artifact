# file: openhands/runtime/base.py:1033-1120
# asked: {"lines": [1038, 1039, 1040, 1041, 1043, 1044, 1046, 1048, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1059, 1060, 1061, 1062, 1063, 1064, 1066, 1067, 1068, 1071, 1073, 1074, 1075, 1076, 1077, 1078, 1080, 1081, 1082, 1083, 1084, 1086, 1087, 1088, 1089, 1090, 1093, 1094, 1095, 1096, 1098, 1100, 1101, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1113, 1116, 1117, 1119, 1120], "branches": [[1038, 1039], [1038, 1099], [1039, 1040], [1039, 1041], [1041, 1043], [1041, 1098], [1048, 1050], [1048, 1071], [1051, 1052], [1051, 1059], [1071, 1073], [1071, 1093], [1099, 1104], [1099, 1105], [1106, 1107], [1106, 1108], [1108, 1109], [1108, 1112], [1112, 1116], [1112, 1119]]}
# gained: {"lines": [1038, 1039, 1040, 1041, 1043, 1044, 1046, 1048, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1059, 1060, 1061, 1062, 1063, 1064, 1066, 1067, 1068, 1071, 1073, 1074, 1075, 1076, 1077, 1078, 1080, 1081, 1082, 1083, 1084, 1086, 1087, 1088, 1089, 1090, 1093, 1094, 1095, 1096, 1100, 1101, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1113, 1116, 1117, 1119, 1120], "branches": [[1038, 1039], [1038, 1099], [1039, 1040], [1039, 1041], [1041, 1043], [1048, 1050], [1048, 1071], [1051, 1052], [1051, 1059], [1071, 1073], [1071, 1093], [1099, 1104], [1099, 1105], [1106, 1107], [1106, 1108], [1108, 1109], [1108, 1112], [1112, 1116], [1112, 1119]]}

import builtins
import types
import pytest

from openhands.events.action import Action, ActionConfirmationStatus
from openhands.events.action.agent import AgentThinkAction, TaskTrackingAction
from openhands.events.observation import AgentThinkObservation, TaskTrackingObservation, ErrorObservation, NullObservation, UserRejectObservation, Observation
import openhands.runtime.base as runtime_module


class FakeFileStore:
    def __init__(self, read_behavior=None, write_behavior=None):
        # read_behavior: callable(path) -> content or raise
        # write_behavior: callable(path, content) -> return or raise
        self.read_behavior = read_behavior
        self.write_behavior = write_behavior
        self.writes = []

    def write(self, path, content):
        self.writes.append((path, content))
        if self.write_behavior:
            return self.write_behavior(path, content)
        return 1

    def read(self, path):
        if self.read_behavior:
            return self.read_behavior(path)
        raise FileNotFoundError()


class FakeEventStream:
    def __init__(self, user_id='user123', file_store=None):
        self.user_id = user_id
        self.file_store = file_store or FakeFileStore()
        self.subscriptions = []

    def subscribe(self, *args, **kwargs):
        # mimic interface; record subscribe for debugging if needed
        self.subscriptions.append((args, kwargs))


class TestRuntime(runtime_module.Runtime):
    def __init__(self, sid='sid123', event_stream=None):
        # Minimal init only for run_action tests
        self.sid = sid
        self.event_stream = event_stream
        # some other attributes that might be expected
        self.user_id = getattr(event_stream, 'user_id', None)

    # Implement all abstract methods with simple stubs to satisfy subclassing
    async def connect(self) -> None:  # pragma: no cover - not used
        return None

    def get_mcp_config(self, extra_stdio_servers=None):
        raise NotImplementedError

    def run(self, action):
        return Observation('run called')

    def run_ipython(self, action):
        return Observation('ipython')

    def read(self, action):
        return Observation('read')

    def write(self, action):
        return Observation('write')

    def edit(self, action):
        return Observation('edit')

    def browse(self, action):
        return Observation('browse')

    def browse_interactive(self, action):
        return Observation('browse_interactive')

    async def call_tool_mcp(self, action):
        return Observation('mcp')

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool=False):
        return None

    def list_files(self, path: str | None=None):
        return []

    def copy_from(self, path: str):
        return None

    @property
    def session_api_key(self):
        return None

    @property
    def vscode_enabled(self):
        return False

    @property
    def vscode_url(self):
        return None

    @property
    def web_hosts(self):
        return {}

    # Add a testable method that can be invoked via action.action
    def do_it(self, action):
        return Observation('executed_do_it')


def test_agent_think_action_returns_agent_think_observation():
    evt = FakeEventStream()
    rt = TestRuntime(event_stream=evt)
    action = AgentThinkAction(thought='I am thinking')
    obs = rt.run_action(action)
    assert isinstance(obs, AgentThinkObservation)
    assert obs.content == 'Your thought has been logged.'


def test_task_tracking_plan_success_and_failure(monkeypatch, tmp_path):
    # Prepare fake conversation dir
    conv_dir = str(tmp_path) + '/'
    monkeypatch.setattr(runtime_module, 'get_conversation_dir', lambda sid, user_id: conv_dir)

    # Success case: write works
    def successful_write(path, content):
        assert path == f'{conv_dir}TASKS.md'
        assert '# Task List' in content
        return 1

    file_store = FakeFileStore(write_behavior=successful_write)
    evt = FakeEventStream(user_id='u1', file_store=file_store)
    rt = TestRuntime(sid='mysid', event_stream=evt)

    action = TaskTrackingAction(command='plan', task_list=[{'title': 'T1', 'notes': 'N1', 'status': 'todo'}])
    obs = rt.run_action(action)
    assert isinstance(obs, TaskTrackingObservation)
    # Check that the message indicates the number of items and path
    assert 'Task list has been updated with 1 items' in obs.content
    assert f'Stored in session directory: {conv_dir}TASKS.md' in obs.content

    # Failure case: write raises
    def failing_write(path, content):
        raise Exception('disk full')

    file_store2 = FakeFileStore(write_behavior=failing_write)
    evt2 = FakeEventStream(user_id='u1', file_store=file_store2)
    rt2 = TestRuntime(sid='mysid', event_stream=evt2)
    action2 = TaskTrackingAction(command='plan', task_list=[{'title': 'T1'}])
    obs2 = rt2.run_action(action2)
    assert isinstance(obs2, ErrorObservation)
    assert 'Failed to write task list to session directory' in obs2.content
    assert 'disk full' in obs2.content


def test_task_tracking_view_variants(monkeypatch, tmp_path):
    conv_dir = str(tmp_path) + '/'
    monkeypatch.setattr(runtime_module, 'get_conversation_dir', lambda sid, user_id: conv_dir)

    # Read success
    def read_ok(path):
        assert path == f'{conv_dir}TASKS.md'
        return 'SOME TASK CONTENT'

    file_store_ok = FakeFileStore(read_behavior=read_ok)
    evt_ok = FakeEventStream(user_id='userX', file_store=file_store_ok)
    rt_ok = TestRuntime(event_stream=evt_ok)
    action_view = TaskTrackingAction(command='view', task_list=[])
    obs_ok = rt_ok.run_action(action_view)
    assert isinstance(obs_ok, TaskTrackingObservation)
    assert obs_ok.content == 'SOME TASK CONTENT'
    assert obs_ok.command == 'view'

    # FileNotFoundError case
    def read_not_found(path):
        raise FileNotFoundError()

    file_store_nf = FakeFileStore(read_behavior=read_not_found)
    evt_nf = FakeEventStream(user_id='userX', file_store=file_store_nf)
    rt_nf = TestRuntime(event_stream=evt_nf)
    obs_nf = rt_nf.run_action(TaskTrackingAction(command='view'))
    assert isinstance(obs_nf, TaskTrackingObservation)
    assert 'No task list found. Use the "plan" command to create one.' == obs_nf.content

    # Generic exception case
    def read_boom(path):
        raise ValueError('boom')

    file_store_boom = FakeFileStore(read_behavior=read_boom)
    evt_boom = FakeEventStream(user_id='userX', file_store=file_store_boom)
    rt_boom = TestRuntime(event_stream=evt_boom)
    obs_boom = rt_boom.run_action(TaskTrackingAction(command='view'))
    assert isinstance(obs_boom, TaskTrackingObservation)
    assert 'Failed to read the task list from session directory' in obs_boom.content
    assert 'boom' in obs_boom.content


def test_task_tracking_unknown_command(monkeypatch, tmp_path):
    conv_dir = str(tmp_path) + '/'
    monkeypatch.setattr(runtime_module, 'get_conversation_dir', lambda sid, user_id: conv_dir)
    file_store = FakeFileStore()
    evt = FakeEventStream(user_id='userZ', file_store=file_store)
    rt = TestRuntime(event_stream=evt)
    action = TaskTrackingAction(command='delete')
    obs = rt.run_action(action)
    assert isinstance(obs, TaskTrackingObservation)
    assert obs.content == 'Unknown command: delete'


def test_runnable_actions_and_confirmation_states(monkeypatch):
    # A runnable action awaiting confirmation -> NullObservation
    class RunnableAction(Action):
        runnable = True
        action = 'will_not_run'

    a = RunnableAction()
    a.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
    rt = TestRuntime(event_stream=FakeEventStream())
    obs = rt.run_action(a)
    assert isinstance(obs, NullObservation)
    assert obs.content == ''

    # action.action not in ACTION_TYPE_TO_CLASS -> ErrorObservation
    b = RunnableAction()
    b.action = 'this_action_does_not_exist_999'
    if hasattr(b, 'confirmation_state'):
        delattr(b, 'confirmation_state')
    obs2 = rt.run_action(b)
    assert isinstance(obs2, ErrorObservation)
    assert 'does not exist' in obs2.content

    # action.action present in ACTION_TYPE_TO_CLASS but runtime lacks attribute -> ErrorObservation
    # Temporarily insert mapping
    monkeypatch.setitem(runtime_module.ACTION_TYPE_TO_CLASS, 'some_custom', RunnableAction)
    c = RunnableAction()
    c.action = 'some_custom'
    obs3 = rt.run_action(c)
    assert isinstance(obs3, ErrorObservation)
    assert 'not supported in the current runtime' in obs3.content

    # action rejected -> UserRejectObservation
    d = RunnableAction()
    d.action = 'some_custom'
    d.confirmation_state = ActionConfirmationStatus.REJECTED
    # Add a dummy method to runtime to ensure mapping step would pass if not rejected
    setattr(rt, 'some_custom', lambda action: Observation('should not be called'))
    obs4 = rt.run_action(d)
    assert isinstance(obs4, UserRejectObservation)
    assert 'Action has been rejected by the user' in obs4.content

    # successful dispatch: runtime has matching method and ACTION_TYPE_TO_CLASS maps to class
    # add mapping for 'do_it' and create action
    monkeypatch.setitem(runtime_module.ACTION_TYPE_TO_CLASS, 'do_it', RunnableAction)
    e = RunnableAction()
    e.action = 'do_it'
    # Ensure runtime has do_it method implemented in TestRuntime
    obs5 = rt.run_action(e)
    assert isinstance(obs5, Observation)
    # Our TestRuntime.do_it returns 'executed_do_it'
    assert obs5.content == 'executed_do_it'
