import types
import pytest
from types import SimpleNamespace
import openhands.runtime.base as base

# Dummy observation and action classes to make returned values observable and deterministic
class DummyAgentThinkObservation:
    def __init__(self, content):
        self.content = content

class DummyTaskTrackingObservation:
    def __init__(self, content=None, command=None, task_list=None):
        self.content = content
        self.command = command
        self.task_list = task_list

class DummyErrorObservation:
    def __init__(self, message):
        self.message = message

class DummyNullObservation:
    def __init__(self, message):
        self.message = message

class DummyUserRejectObservation:
    def __init__(self, message):
        self.message = message

class DummyAgentThinkAction:
    def __init__(self, runnable=False):
        self.runnable = runnable

class DummyTaskTrackingAction:
    def __init__(self, runnable=False, command=None, task_list=None):
        self.runnable = runnable
        self.command = command
        self.task_list = task_list or []

# Simple fake file store to simulate read/write behaviors deterministically
class DummyFileStore:
    def __init__(self, read_result=None, read_exc=None, write_exc=None):
        self.read_result = read_result
        self.read_exc = read_exc
        self.write_exc = write_exc
        self.written = []

    def write(self, path, content):
        if self.write_exc:
            raise self.write_exc
        self.written.append((path, content))

    def read(self, path):
        if self.read_exc:
            raise self.read_exc
        return self.read_result

# Minimal self-like object for calling the unbound method Runtime.run_action
class SelfStub:
    def __init__(self, file_store=None, sid='SID123', user_id='USER123'):
        self.sid = sid
        es = SimpleNamespace()
        es.user_id = user_id
        es.file_store = file_store or DummyFileStore()
        self.event_stream = es


@pytest.fixture(autouse=True)
def patch_runtime_names(monkeypatch):
    """Patch naming in the runtime module so run_action constructs our dummy observations and recognizes our dummy actions.
    This fixture is applied automatically to all tests in this module.
    """
    # Patch the classes used for isinstance checks and instantiation
    monkeypatch.setattr(base, 'AgentThinkAction', DummyAgentThinkAction)
    monkeypatch.setattr(base, 'TaskTrackingAction', DummyTaskTrackingAction)

    # Patch the observation classes that run_action instantiates so we can inspect returned values
    monkeypatch.setattr(base, 'AgentThinkObservation', DummyAgentThinkObservation)
    monkeypatch.setattr(base, 'TaskTrackingObservation', DummyTaskTrackingObservation)
    monkeypatch.setattr(base, 'ErrorObservation', DummyErrorObservation)
    monkeypatch.setattr(base, 'NullObservation', DummyNullObservation)
    monkeypatch.setattr(base, 'UserRejectObservation', DummyUserRejectObservation)

    # Patch get_conversation_dir to a deterministic path
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/session_dir/')

    # Provide a lightweight ActionConfirmationStatus replacement for deterministic comparisons
    monkeypatch.setattr(base, 'ActionConfirmationStatus', SimpleNamespace(AWAITING_CONFIRMATION='AWAIT', REJECTED='REJ'))

    yield


def test_agent_think_not_runnable_round_039():
    action = DummyAgentThinkAction(runnable=False)
    self_stub = SelfStub()

    obs = base.Runtime.run_action(self_stub, action)

    # Expect our patched AgentThinkObservation to be returned with exact message
    assert isinstance(obs, DummyAgentThinkObservation)
    assert obs.content == 'Your thought has been logged.'


def test_tasktracking_plan_success_round_039():
    task_list = [
        {'title': 'Task A', 'notes': 'Note A', 'status': 'todo'},
        {'title': 'Task B', 'notes': 'Note B', 'status': 'done'},
    ]
    action = DummyTaskTrackingAction(runnable=False, command='plan', task_list=task_list)
    store = DummyFileStore()
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    # Ensure the file_store.write was called and returned TaskTrackingObservation reports updated count
    assert store.written, 'Expected write to be called for plan command'
    path, content = store.written[0]
    assert path == '/session_dir/TASKS.md'
    assert '# Task List' in content
    assert '1.' in content and '2.' in content

    assert isinstance(obs, DummyTaskTrackingObservation)
    assert obs.command == 'plan'
    assert obs.task_list == task_list
    assert 'Task list has been updated with 2 items' in obs.content


def test_tasktracking_plan_write_exception_round_039():
    task_list = [{'title': 'X', 'notes': 'Y'}]
    action = DummyTaskTrackingAction(runnable=False, command='plan', task_list=task_list)
    store = DummyFileStore(write_exc=Exception('disk error'))
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    # When write raises, run_action returns ErrorObservation with the exception message
    assert isinstance(obs, DummyErrorObservation)
    assert 'Failed to write task list to session directory' in obs.message
    assert 'disk error' in obs.message


def test_tasktracking_view_success_round_039():
    action = DummyTaskTrackingAction(runnable=False, command='view')
    store = DummyFileStore(read_result='EXISTING TASKS CONTENT')
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    assert isinstance(obs, DummyTaskTrackingObservation)
    assert obs.command == 'view'
    assert obs.content == 'EXISTING TASKS CONTENT'
    assert obs.task_list == []


def test_tasktracking_view_file_not_found_round_039():
    action = DummyTaskTrackingAction(runnable=False, command='view')
    store = DummyFileStore(read_exc=FileNotFoundError())
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    assert isinstance(obs, DummyTaskTrackingObservation)
    assert obs.command == 'view'
    assert obs.task_list == []
    assert obs.content == 'No task list found. Use the "plan" command to create one.'


def test_tasktracking_view_other_exception_round_039():
    action = DummyTaskTrackingAction(runnable=False, command='view')
    store = DummyFileStore(read_exc=Exception('io problem'))
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    assert isinstance(obs, DummyTaskTrackingObservation)
    assert 'Failed to read the task list from session directory' in obs.content
    assert 'io problem' in obs.content


def test_tasktracking_unknown_command_round_039():
    action = DummyTaskTrackingAction(runnable=False, command='foobar')
    store = DummyFileStore()
    self_stub = SelfStub(file_store=store)

    obs = base.Runtime.run_action(self_stub, action)

    assert isinstance(obs, DummyTaskTrackingObservation)
    assert obs.command == 'foobar'
    assert obs.content == 'Unknown command: foobar'


def test_awaiting_confirmation_returns_null_round_039():
    # A runnable action that is awaiting confirmation should return NullObservation
    action = SimpleNamespace(runnable=True, confirmation_state='AWAIT')
    self_stub = SelfStub()

    obs = base.Runtime.run_action(self_stub, action)

    assert isinstance(obs, DummyNullObservation)
    assert obs.message == ''


def test_action_type_not_in_mapping_returns_error_round_039():
    # Ensure that an action whose .action is not in ACTION_TYPE_TO_CLASS returns ErrorObservation
    action = SimpleNamespace(runnable=True, action='nonexistent_action')
    self_stub = SelfStub()

    # Ensure mapping does not include the key
    # Use monkeypatch via direct replacement so this test is deterministic
    original_map = base.ACTION_TYPE_TO_CLASS
    try:
        base.ACTION_TYPE_TO_CLASS = {}
        obs = base.Runtime.run_action(self_stub, action)
    finally:
        base.ACTION_TYPE_TO_CLASS = original_map

    assert isinstance(obs, DummyErrorObservation)
    assert 'Action nonexistent_action does not exist.' in obs.message


def test_action_not_supported_returns_error_round_039():
    # If the action type exists in mapping but the runtime does not implement a corresponding method,
    # an ErrorObservation is returned indicating lack of support.
    action_type = 'some_action'
    action = SimpleNamespace(runnable=True, action=action_type)
    self_stub = SelfStub()

    original_map = base.ACTION_TYPE_TO_CLASS
    try:
        base.ACTION_TYPE_TO_CLASS = {action_type: object}
        obs = base.Runtime.run_action(self_stub, action)
    finally:
        base.ACTION_TYPE_TO_CLASS = original_map

    assert isinstance(obs, DummyErrorObservation)
    assert 'is not supported in the current runtime' in obs.message


def test_rejected_confirmation_returns_user_reject_round_039():
    # If an action has been rejected, return UserRejectObservation even if runtime implements method
    action_type = 'do_it'
    action = SimpleNamespace(runnable=True, action=action_type, confirmation_state='REJ')

    # Provide a self stub that *does* have the method so we pass the hasattr check
    def dummy_impl(a):
        return DummyTaskTrackingObservation(content='should not be used', command=action_type, task_list=[])

    self_stub = SelfStub()
    setattr(self_stub, action_type, dummy_impl)

    original_map = base.ACTION_TYPE_TO_CLASS
    try:
        base.ACTION_TYPE_TO_CLASS = {action_type: object}
        obs = base.Runtime.run_action(self_stub, action)
    finally:
        base.ACTION_TYPE_TO_CLASS = original_map

    assert isinstance(obs, DummyUserRejectObservation)
    assert 'Action has been rejected by the user' in obs.message
