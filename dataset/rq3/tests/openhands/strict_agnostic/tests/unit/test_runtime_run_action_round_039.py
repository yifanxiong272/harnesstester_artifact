import importlib
import types
import pytest

base_mod = importlib.import_module('openhands.runtime.base')
# Disable abstractmethod enforcement on Runtime so we can instantiate a test double
setattr(base_mod.Runtime, '__abstractmethods__', set())
from openhands.runtime.base import Runtime
from openhands.events.action import AgentThinkAction, TaskTrackingAction
from openhands.events.action import ActionConfirmationStatus
from openhands.events.observation import (
    AgentThinkObservation,
    CmdOutputObservation,
    ErrorObservation,
    FileReadObservation,
    NullObservation,
    Observation,
    TaskTrackingObservation,
    UserRejectObservation,
)


def _make_runtime(file_store=None, sid='sid123', user_id='user123'):
    """Create a Runtime instance without calling __init__ and attach a simple event_stream and sid."""
    inst = object.__new__(base_mod.Runtime)
    inst.sid = sid
    # simple event_stream with user_id and file_store attributes
    inst.event_stream = types.SimpleNamespace(user_id=user_id, file_store=file_store)
    return inst


class DummyFileStore:
    def __init__(self, read_result=None, read_exc=None, write_exc=None):
        self.read_result = read_result
        self.read_exc = read_exc
        self.write_exc = write_exc
        self.written = None

    def write(self, path, content):
        if self.write_exc:
            raise self.write_exc
        self.written = (path, content)

    def read(self, path):
        if self.read_exc:
            raise self.read_exc
        return self.read_result


def _get_content_str(obs):
    # Many observation classes store text on .content; fall back to str(obs)
    return getattr(obs, 'content', None) or getattr(obs, 'message', None) or str(obs)


def test_agent_think_round_039(monkeypatch):
    # AgentThinkAction when not runnable should return AgentThinkObservation with exact message
    action = AgentThinkAction.__new__(AgentThinkAction)
    action.runnable = False

    rt = _make_runtime()

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, AgentThinkObservation)
    assert 'Your thought has been logged.' in _get_content_str(obs)


def test_task_tracking_plan_success_round_039(monkeypatch):
    # TaskTrackingAction with command 'plan' should write TASKS.md and return TaskTrackingObservation
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'plan'
    action.task_list = [
        {'title': 'First task', 'notes': 'Notes1', 'status': 'todo'},
        {'title': 'Second', 'notes': '', 'status': 'done'},
    ]

    # ensure get_conversation_dir returns deterministic path
    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')

    fs = DummyFileStore()
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    # Expecting a TaskTrackingObservation and file written at expected path
    assert isinstance(obs, TaskTrackingObservation)
    assert obs.command == 'plan'
    assert obs.task_list == action.task_list
    assert 'Task list has been updated' in _get_content_str(obs)

    # file store should have been called with TASKS.md under the conversation dir
    assert fs.written is not None
    path, content = fs.written
    assert path == '/fake/session/TASKS.md'
    # content should include task titles and notes
    assert '1. ' in content and 'First task' in content and 'Notes1' in content
    assert '2. ' in content and 'Second' in content


def test_task_tracking_plan_write_exception_round_039(monkeypatch):
    # If write raises, run_action should return an ErrorObservation with the exception message
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'plan'
    action.task_list = [{'title': 'T', 'notes': '', 'status': 'todo'}]

    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')

    fs = DummyFileStore(write_exc=Exception('disk full'))
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, ErrorObservation)
    assert 'Failed to write task list' in _get_content_str(obs)
    assert 'disk full' in _get_content_str(obs)


def test_task_tracking_view_success_round_039(monkeypatch):
    # view command should read and return content
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'view'

    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')
    fs = DummyFileStore(read_result='SAVED TASKS')
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, TaskTrackingObservation)
    assert obs.command == 'view'
    # content should be the file content returned
    assert 'SAVED TASKS' in _get_content_str(obs)
    assert obs.task_list == []


def test_task_tracking_view_file_not_found_round_039(monkeypatch):
    # view when file not found should return a helpful message
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'view'

    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')
    fs = DummyFileStore(read_exc=FileNotFoundError())
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, TaskTrackingObservation)
    assert obs.command == 'view'
    assert 'No task list found' in _get_content_str(obs)
    assert obs.task_list == []


def test_task_tracking_view_other_exception_round_039(monkeypatch):
    # view when read raises a non-FileNotFoundError should return an error-containing TaskTrackingObservation
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'view'

    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')
    fs = DummyFileStore(read_exc=RuntimeError('boom'))
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, TaskTrackingObservation)
    assert obs.command == 'view'
    assert 'Failed to read the task list' in _get_content_str(obs)
    assert 'boom' in _get_content_str(obs)


def test_task_tracking_unknown_command_round_039(monkeypatch):
    # unknown task tracking command should return Unknown command message
    action = TaskTrackingAction.__new__(TaskTrackingAction)
    action.runnable = False
    action.command = 'delete'

    monkeypatch.setattr(base_mod, 'get_conversation_dir', lambda sid, user_id: '/fake/session/')
    fs = DummyFileStore()
    rt = _make_runtime(file_store=fs)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, TaskTrackingObservation)
    assert 'Unknown command: delete' in _get_content_str(obs)


def test_confirmation_awaiting_round_039():
    # If confirmation_state is AWAITING_CONFIRMATION and action.runnable True -> NullObservation
    action = types.SimpleNamespace(runnable=True, confirmation_state=ActionConfirmationStatus.AWAITING_CONFIRMATION)
    rt = _make_runtime()

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, NullObservation)


def test_action_type_not_exist_round_039(monkeypatch):
    # If action_type not in ACTION_TYPE_TO_CLASS -> ErrorObservation
    action = types.SimpleNamespace(runnable=True, action='nonexistent', confirmation_state=None)

    # force ACTION_TYPE_TO_CLASS empty for this test
    monkeypatch.setattr(base_mod, 'ACTION_TYPE_TO_CLASS', {})

    rt = _make_runtime()

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, ErrorObservation)
    assert 'Action nonexistent does not exist.' in _get_content_str(obs)


def test_action_not_supported_in_runtime_round_039(monkeypatch):
    # If action_type exists in ACTION_TYPE_TO_CLASS but runtime lacks the method -> ErrorObservation
    action = types.SimpleNamespace(runnable=True, action='do', confirmation_state=None)

    monkeypatch.setattr(base_mod, 'ACTION_TYPE_TO_CLASS', {'do': object})

    rt = _make_runtime()
    # ensure rt has no attribute 'do'
    if hasattr(rt, 'do'):
        delattr(rt, 'do')

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, ErrorObservation)
    assert 'Action do is not supported in the current runtime.' in _get_content_str(obs)


def test_confirmation_rejected_round_039(monkeypatch):
    # If confirmation_state is REJECTED -> UserRejectObservation without calling action handler
    action = types.SimpleNamespace(runnable=True, action='anything', confirmation_state=ActionConfirmationStatus.REJECTED)

    monkeypatch.setattr(base_mod, 'ACTION_TYPE_TO_CLASS', {'anything': object})

    rt = _make_runtime()

    # provide a handler so if it were called we would see a different result; should NOT be called
    def handler(a):
        return NullObservation('should not be reached')

    setattr(rt, 'anything', handler)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, UserRejectObservation)
    assert 'Action has been rejected by the user' in _get_content_str(obs)


def test_action_invokes_runtime_method_round_039(monkeypatch):
    # When action exists and runtime has handler and no rejection/awaiting, the handler's returned observation is forwarded
    action = types.SimpleNamespace(runnable=True, action='runme', confirmation_state=None)

    monkeypatch.setattr(base_mod, 'ACTION_TYPE_TO_CLASS', {'runme': object})

    rt = _make_runtime()

    def handler(a):
        return NullObservation('handler-ok')

    # attach bound method
    setattr(rt, 'runme', handler)

    obs = base_mod.Runtime.run_action(rt, action)

    assert isinstance(obs, NullObservation)
    assert 'handler-ok' in _get_content_str(obs)
