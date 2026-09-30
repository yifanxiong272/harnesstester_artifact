import types
import pytest
import builtins

import openhands.runtime.base as base

# Helper fake classes and fixtures
class FakeAgentThink:
    def __init__(self):
        self.runnable = False

class FakeTaskTracking:
    def __init__(self, command='plan', task_list=None):
        self.runnable = False
        self.command = command
        self.task_list = task_list or []

class FakeGenericAction:
    def __init__(self, runnable=True, action_name='do_something', confirmation_state=None):
        self.runnable = runnable
        self.action = action_name
        if confirmation_state is not None:
            self.confirmation_state = confirmation_state

class DummyFileStore:
    def __init__(self, read_behavior=None, write_behavior=None):
        # read_behavior and write_behavior can be callables or exceptions
        self._read_behavior = read_behavior
        self._write_behavior = write_behavior
        self.writes = []

    def write(self, path, content):
        self.writes.append((path, content))
        if isinstance(self._write_behavior, Exception):
            raise self._write_behavior
        if callable(self._write_behavior):
            return self._write_behavior(path, content)
        return None

    def read(self, path):
        if isinstance(self._read_behavior, Exception):
            raise self._read_behavior
        if callable(self._read_behavior):
            return self._read_behavior(path)
        return self._read_behavior

class FakeEventStream:
    def __init__(self, file_store=None, user_id='user'):
        self.file_store = file_store or DummyFileStore()
        self.user_id = user_id


def run_action_on(obj_self, action):
    """Utility to call the bound Runtime.run_action method using a lightweight fake self."""
    return base.Runtime.run_action.__get__(obj_self, base.Runtime)(action)


# Tests

def test_agent_think_action_round_039(monkeypatch):
    # Patch the symbol used for isinstance checks inside run_action
    monkeypatch.setattr(base, 'AgentThinkAction', FakeAgentThink)

    fake_self = types.SimpleNamespace()
    action = FakeAgentThink()

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.AgentThinkObservation)
    # The implementation returns a specific message; assert it is present
    assert getattr(obs, 'content', None) == 'Your thought has been logged.' or str(obs).find('Your thought has been logged.') != -1


def test_task_tracking_plan_success_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore(read_behavior=None, write_behavior=None)
    event_stream = FakeEventStream(file_store=file_store, user_id='u')
    fake_self = types.SimpleNamespace(sid='S1', event_stream=event_stream)

    action = FakeTaskTracking(command='plan', task_list=[{'title': 'T1', 'notes': 'N1', 'status': 'todo'}, {'title': 'T2'}])

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.TaskTrackingObservation)
    # Check returned observation message references the number of items and file path
    assert 'Task list has been updated with 2 items' in getattr(obs, 'content', '')
    # ensure write was called to the expected task file
    assert file_store.writes, 'expected file_store.write to be called'
    path, content = file_store.writes[0]
    assert path.endswith('TASKS.md')
    # content should contain task titles and numbering
    assert '1.' in content and 'T1' in content


def test_task_tracking_plan_write_error_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore(read_behavior=None, write_behavior=Exception('disk full'))
    event_stream = FakeEventStream(file_store=file_store)
    fake_self = types.SimpleNamespace(sid='S2', event_stream=event_stream)

    action = FakeTaskTracking(command='plan', task_list=[{'title': 'Only', 'notes': ''}])

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.ErrorObservation)
    # Error message should include the task_file_path and the exception text
    assert 'TASKS.md' in getattr(obs, 'content', str(obs)) or 'TASKS.md' in str(obs)
    assert 'disk full' in getattr(obs, 'content', str(obs)) or 'disk full' in str(obs)


def test_task_tracking_view_success_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore(read_behavior='SAVED CONTENT')
    event_stream = FakeEventStream(file_store=file_store)
    fake_self = types.SimpleNamespace(sid='S3', event_stream=event_stream)

    action = FakeTaskTracking(command='view')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.TaskTrackingObservation)
    assert getattr(obs, 'content', None) == 'SAVED CONTENT'


def test_task_tracking_view_not_found_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore(read_behavior=FileNotFoundError())
    # The DummyFileStore raising FileNotFoundError needs to be an actual exception instance
    file_store._read_behavior = FileNotFoundError()
    event_stream = FakeEventStream(file_store=file_store)
    fake_self = types.SimpleNamespace(sid='S4', event_stream=event_stream)

    action = FakeTaskTracking(command='view')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.TaskTrackingObservation)
    assert 'No task list found. Use the "plan" command to create one.' in getattr(obs, 'content', '')


def test_task_tracking_view_read_error_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore(read_behavior=RuntimeError('korrupt'))
    event_stream = FakeEventStream(file_store=file_store)
    fake_self = types.SimpleNamespace(sid='S5', event_stream=event_stream)

    action = FakeTaskTracking(command='view')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.TaskTrackingObservation)
    assert 'Failed to read the task list' in getattr(obs, 'content', '')
    assert 'korrupt' in getattr(obs, 'content', '')


def test_task_tracking_unknown_command_round_039(monkeypatch):
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)
    monkeypatch.setattr(base, 'get_conversation_dir', lambda sid, user_id: '/fake/convo/')

    file_store = DummyFileStore()
    event_stream = FakeEventStream(file_store=file_store)
    fake_self = types.SimpleNamespace(sid='S6', event_stream=event_stream)

    action = FakeTaskTracking(command='delete')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.TaskTrackingObservation)
    assert getattr(obs, 'content', '').strip() == f'Unknown command: {action.command}'


def test_non_runnable_null_observation_round_039(monkeypatch):
    # Ensure AgentThinkAction and TaskTrackingAction are types that our fake won't match
    monkeypatch.setattr(base, 'AgentThinkAction', FakeAgentThink)
    monkeypatch.setattr(base, 'TaskTrackingAction', FakeTaskTracking)

    class Other:
        def __init__(self):
            self.runnable = False

    fake_self = types.SimpleNamespace()
    action = Other()

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.NullObservation)


def test_awaiting_confirmation_round_039(monkeypatch):
    # Patch ActionConfirmationStatus used for equality checks
    C = types.SimpleNamespace(AWAITING_CONFIRMATION='AWAIT', REJECTED='REJ')
    monkeypatch.setattr(base, 'ActionConfirmationStatus', C)

    fake_self = types.SimpleNamespace()
    action = FakeGenericAction(runnable=True, action_name='anything', confirmation_state='AWAIT')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.NullObservation)


def test_action_type_not_exist_round_039(monkeypatch):
    # Ensure no mapping exists
    monkeypatch.setattr(base, 'ACTION_TYPE_TO_CLASS', {}, raising=False)

    fake_self = types.SimpleNamespace()
    action = FakeGenericAction(runnable=True, action_name='nope')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.ErrorObservation)
    assert 'Action nope does not exist.' in getattr(obs, 'content', str(obs)) or 'Action nope does not exist.' in str(obs)


def test_action_not_supported_in_runtime_round_039(monkeypatch):
    # Put a mapping so the type exists
    monkeypatch.setattr(base, 'ACTION_TYPE_TO_CLASS', {'do_something': object()}, raising=False)

    fake_self = types.SimpleNamespace()
    action = FakeGenericAction(runnable=True, action_name='do_something')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.ErrorObservation)
    assert 'is not supported in the current runtime' in getattr(obs, 'content', str(obs)) or 'is not supported in the current runtime' in str(obs)


def test_action_rejected_round_039(monkeypatch):
    # Make sure the action type is recognized and supported by the runtime
    monkeypatch.setattr(base, 'ACTION_TYPE_TO_CLASS', {'do_something': object()}, raising=False)
    C = types.SimpleNamespace(AWAITING_CONFIRMATION='AWAIT', REJECTED='REJ')
    monkeypatch.setattr(base, 'ActionConfirmationStatus', C)

    # Provide a runtime attribute so hasattr passes
    def dummy_handler(a):
        return base.NullObservation('handled')

    fake_self = types.SimpleNamespace(do_something=dummy_handler)
    action = FakeGenericAction(runnable=True, action_name='do_something', confirmation_state='REJ')

    obs = run_action_on(fake_self, action)

    assert isinstance(obs, base.UserRejectObservation)
    assert 'Action has been rejected' in (getattr(obs, 'content', '') or str(obs)) or 'rejected' in str(obs).lower()
