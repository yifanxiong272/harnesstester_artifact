import asyncio
import os
import threading
import types
import pytest

import openhands.runtime.impl.local.local_runtime as lr_mod
from openhands.core.exceptions import AgentRuntimeDisconnectedError

class _DummyProcess:
    def __init__(self, poll_return):
        self._poll = poll_return

    def poll(self):
        return self._poll

class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

@pytest.mark.asyncio
async def test_runtime_not_initialized_round_054():
    # Create an instance bypassing __init__ and set internal _runtime_initialized False
    inst = object.__new__(lr_mod.LocalRuntime)
    # runtime_initialized is a read-only property; set the backing attribute
    inst._runtime_initialized = False

    with pytest.raises(AgentRuntimeDisconnectedError) as exc:
        await lr_mod.LocalRuntime.execute_action(inst, action=object())
    assert 'Runtime not initialized' in str(exc.value)

@pytest.mark.asyncio
async def test_server_process_none_sid_not_in_running_round_054(monkeypatch):
    # runtime initialized but server_process is None and sid not present -> Server process not found
    inst = object.__new__(lr_mod.LocalRuntime)
    inst._runtime_initialized = True
    inst.server_process = None
    inst.sid = 'unique-sid-not-present'
    # Ensure global dict has no entry for this sid
    monkeypatch.setattr(lr_mod, '_RUNNING_SERVERS', {}, raising=False)

    # Minimal attributes needed for method flow
    inst.action_semaphore = threading.Lock()
    inst.session = None
    inst.api_url = 'http://unused'
    inst.log = lambda *a, **k: None

    with pytest.raises(AgentRuntimeDisconnectedError) as exc:
        await lr_mod.LocalRuntime.execute_action(inst, action=object())
    assert 'Server process not found' in str(exc.value)

@pytest.mark.asyncio
async def test_server_process_none_in_running_triggers_warm_create_round_054(monkeypatch):
    # server_process None but sid in _RUNNING_SERVERS -> should pick up process and proceed
    inst = object.__new__(lr_mod.LocalRuntime)
    inst._runtime_initialized = True
    inst.server_process = None
    inst.sid = 'sid-warm'

    # Create a running process (poll() returns None)
    running_proc = _DummyProcess(poll_return=None)
    monkeypatch.setattr(lr_mod, '_RUNNING_SERVERS', {inst.sid: types.SimpleNamespace(process=running_proc)}, raising=False)

    # Prepare to capture warm server creation calls
    created = {'called': False}

    def fake_create_warm(config, plugins):
        created['called'] = True

    monkeypatch.setattr(lr_mod, '_create_warm_server_in_background', fake_create_warm, raising=False)

    # Patch call_sync_from_async to synchronously call the provided callable
    async def fake_call_sync_from_async(func):
        return func()

    monkeypatch.setattr(lr_mod, 'call_sync_from_async', fake_call_sync_from_async, raising=True)

    # Patch event_to_dict and observation_from_dict to be identity functions for determinism
    monkeypatch.setattr(lr_mod, 'event_to_dict', lambda a: {'action_received': True}, raising=True)
    monkeypatch.setattr(lr_mod, 'observation_from_dict', lambda d: d, raising=True)

    # Fake response object returned by session.post
    fake_resp = _DummyResponse({'ok': True})
    class DummySession:
        def post(self, url, json):
            assert '/execute_action' in url
            # Ensure event_to_dict was used and shape preserved
            assert json == {'action': {'action_received': True}}
            return fake_resp

    inst.session = DummySession()
    inst.api_url = 'http://example'
    inst.action_semaphore = threading.Lock()
    inst.log = lambda level, msg: None
    inst.config = {'cfg': 1}
    inst.plugins = ['p']

    # Ensure there are fewer warm servers than desired so creation is triggered
    monkeypatch.setattr(lr_mod, '_WARM_SERVERS', {}, raising=False)
    monkeypatch.setenv('DESIRED_NUM_WARM_SERVERS', '1')

    result = await lr_mod.LocalRuntime.execute_action(inst, action=object())
    assert result == {'ok': True}
    assert created['called'] is True

@pytest.mark.asyncio
async def test_server_process_dead_removes_running_and_raises_round_054(monkeypatch):
    # server_process.poll() != None should remove entry from _RUNNING_SERVERS and raise
    inst = object.__new__(lr_mod.LocalRuntime)
    inst._runtime_initialized = True
    inst.sid = 'sid-dead'
    # attach a process that reports not None (dead)
    dead_proc = _DummyProcess(poll_return=1)
    inst.server_process = dead_proc

    # Put entry in _RUNNING_SERVERS that should be deleted
    global_running = {inst.sid: types.SimpleNamespace(process=dead_proc)}
    monkeypatch.setattr(lr_mod, '_RUNNING_SERVERS', global_running, raising=False)

    inst.action_semaphore = threading.Lock()
    inst.session = None
    inst.api_url = 'http://x'
    inst.log = lambda *a, **k: None

    with pytest.raises(AgentRuntimeDisconnectedError) as exc:
        await lr_mod.LocalRuntime.execute_action(inst, action=object())
    assert 'Server process died' in str(exc.value)
    # Confirm entry was removed
    assert inst.sid not in lr_mod._RUNNING_SERVERS

@pytest.mark.asyncio
async def test_network_error_converts_to_agent_disconnected_round_054(monkeypatch):
    # Simulate a network error raised by call_sync_from_async
    inst = object.__new__(lr_mod.LocalRuntime)
    inst._runtime_initialized = True
    inst.server_process = _DummyProcess(poll_return=None)
    inst.sid = 'sid-net'

    monkeypatch.setattr(lr_mod, '_RUNNING_SERVERS', {inst.sid: types.SimpleNamespace(process=inst.server_process)}, raising=False)

    async def raising_call_sync(func):
        raise lr_mod.httpx.NetworkError('simulated')

    monkeypatch.setattr(lr_mod, 'call_sync_from_async', raising_call_sync, raising=True)

    inst.action_semaphore = threading.Lock()
    inst.session = types.SimpleNamespace()
    inst.api_url = 'http://x'
    inst.log = lambda *a, **k: None

    with pytest.raises(AgentRuntimeDisconnectedError) as exc:
        await lr_mod.LocalRuntime.execute_action(inst, action=object())
    assert 'Server connection lost' in str(exc.value)
