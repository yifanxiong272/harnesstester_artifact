import asyncio
import types
import pytest
import docker

import importlib
docker_runtime = importlib.import_module('openhands.runtime.impl.docker.docker_runtime')
from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.runtime.runtime_status import RuntimeStatus


class FakeLogStreamer:
    def __init__(self, container, log):
        self.container = container
        self.log = log


class DummyNetwork:
    def __init__(self, name, record):
        self.name = name
        self.record = record

    def connect(self, container):
        # record that connect was called with the container
        self.record.append((self.name, container))


class DummySandbox:
    def __init__(self, additional_networks):
        self.additional_networks = additional_networks


class DummyDockerClient:
    def __init__(self, mapping):
        # mapping: network_name -> either DummyNetwork or exception to raise
        self._mapping = mapping
        self.networks = types.SimpleNamespace()
        self.networks.get = self._get

    def _get(self, name):
        value = self._mapping.get(name)
        if isinstance(value, Exception):
            raise value
        return value


class DummySelf:
    def __init__(self):
        # defaults
        self.attach_to_existing = False
        self.container_name = 'ctr-1'
        self.runtime_container_image = 'img:latest'
        self.plugins = []
        self.config = types.SimpleNamespace()
        self.config.sandbox = DummySandbox([])
        self.docker_client = DummyDockerClient({})
        self.container = None
        self._runtime_initialized = False
        self.logged = []
        self.statuses = []
        # hooks to observe calls
        self._maybe_built = False
        self._inited = False
        self._waited = False
        self._setup_initial_env = False
        # expose log_streamer that code will set
        self.log_streamer = None
        # attributes accessed by connect logging
        self.vscode_url = 'http://vscode'
        self.api_url = 'http://api'

    def log(self, level, msg):
        # record messages for assertions
        self.logged.append((level, msg))

    def set_runtime_status(self, status):
        self.statuses.append(status)

    def maybe_build_runtime_container_image(self):
        self._maybe_built = True

    def init_container(self):
        # simulate starting a container
        self._inited = True
        # create a simple object to represent the container
        self.container = types.SimpleNamespace(name=self.container_name)

    def wait_until_alive(self):
        self._waited = True

    def setup_initial_env(self):
        self._setup_initial_env = True


# helper to replace call_sync_from_async in the module: returns coroutine executing the callable
async def _async_call_sync_from_async(func):
    # If func is a coroutine function, run it
    result = func()
    return result


@pytest.mark.asyncio
async def test_connect_attach_to_existing_true_round_018(monkeypatch):
    """When attach_to_existing is True and _attach_to_container raises NotFound,
    DockerRuntime.connect should log a warning and raise AgentRuntimeDisconnectedError.
    """
    dummy = DummySelf()
    dummy.attach_to_existing = True

    # make _attach_to_container raise docker.errors.NotFound
    def _attach():
        raise docker.errors.NotFound('no such container')

    dummy._attach_to_container = _attach

    # ensure call_sync_from_async in module awaits our async wrapper
    monkeypatch.setattr(docker_runtime, 'call_sync_from_async', _async_call_sync_from_async)

    # capture logging done by the instance
    with pytest.raises(AgentRuntimeDisconnectedError):
        await docker_runtime.DockerRuntime.connect(dummy)

    # verify the warning log was emitted mentioning the container name
    assert any(lvl == 'warning' and dummy.container_name in msg for (lvl, msg) in dummy.logged), (
        'Expected a warning log mentioning the missing container'
    )


@pytest.mark.asyncio
async def test_connect_attach_to_existing_false_with_container_round_018(monkeypatch):
    """When attach_to_existing is False and attach raises NotFound, the runtime should build
    the image, initialize a container, set up env, possibly create a LogStreamer (when DEBUG_RUNTIME is True),
    set status to READY, and attempt to connect to networks, logging errors for failing networks.
    """
    dummy = DummySelf()
    dummy.attach_to_existing = False

    # _attach_to_container raises NotFound -> branch that builds and initializes
    def _attach():
        raise docker.errors.NotFound('missing')

    dummy._attach_to_container = _attach

    # Prepare networks: one that will connect successfully, one that will cause get() to raise
    connect_records = []
    ok_network = DummyNetwork('net_ok', connect_records)
    err_exc = Exception('network failure')
    dummy.config.sandbox.additional_networks = ['net_ok', 'net_err']
    dummy.docker_client = DummyDockerClient({'net_ok': ok_network, 'net_err': err_exc})

    # Provide plugins list to exercise debug log line formatting
    plugin = types.SimpleNamespace(name='plug1')
    dummy.plugins = [plugin]

    # monkeypatch module DEBUG_RUNTIME True so LogStreamer path used
    monkeypatch.setattr(docker_runtime, 'DEBUG_RUNTIME', True)
    # monkeypatch LogStreamer to our FakeLogStreamer so no external behavior
    monkeypatch.setattr(docker_runtime, 'LogStreamer', FakeLogStreamer)

    # use the async call wrapper so awaits inside connect work
    monkeypatch.setattr(docker_runtime, 'call_sync_from_async', _async_call_sync_from_async)

    # run connect
    await docker_runtime.DockerRuntime.connect(dummy)

    # After connect, maybe_build_runtime_container_image should have been invoked
    assert dummy._maybe_built is True
    # init_container should have been called, creating a container object
    assert dummy._inited is True and dummy.container is not None
    # wait_until_alive and setup_initial_env should have been invoked
    assert dummy._waited is True
    assert dummy._setup_initial_env is True

    # LogStreamer should have been constructed with the container and dummy.log
    assert isinstance(dummy.log_streamer, FakeLogStreamer)
    assert dummy.log_streamer.container is dummy.container

    # Runtime status should include READY as last or one of statuses
    assert any(s == RuntimeStatus.READY for s in dummy.statuses), 'Expected runtime to be set to READY'

    # network connect should have been called for net_ok
    assert any(rec[0] == 'net_ok' and rec[1] is dummy.container for rec in connect_records)

    # error log for net_err should have been emitted
    assert any(lvl == 'error' and 'Failed to connect instance' in msg for (lvl, msg) in dummy.logged), (
        'Expected an error log for failing to connect to a network'
    )


@pytest.mark.asyncio
async def test_connect_attach_to_existing_false_no_container_round_018(monkeypatch):
    """When attach_to_existing is False and the initialized container is missing (None),
    the network loop should log a warning about container not being available. Also when
    DEBUG_RUNTIME is False, log_streamer should be None.
    """
    dummy = DummySelf()
    dummy.attach_to_existing = False

    # _attach_to_container raises NotFound -> branch that builds and initializes
    def _attach():
        raise docker.errors.NotFound('missing')

    dummy._attach_to_container = _attach

    # configure sandbox networks such that the network exists but container remains None
    connect_records = []
    ok_network = DummyNetwork('net_warn', connect_records)
    dummy.config.sandbox.additional_networks = ['net_warn']
    dummy.docker_client = DummyDockerClient({'net_warn': ok_network})

    # Make DEBUG_RUNTIME False to hit the else branch where log_streamer is None
    monkeypatch.setattr(docker_runtime, 'DEBUG_RUNTIME', False)
    monkeypatch.setattr(docker_runtime, 'call_sync_from_async', _async_call_sync_from_async)

    # Override init_container so container stays None (simulate failure to start container)
    def init_container_noop():
        dummy._inited = True
        dummy.container = None

    dummy.init_container = init_container_noop

    await docker_runtime.DockerRuntime.connect(dummy)

    # Check log_streamer is None in this branch
    assert dummy.log_streamer is None

    # Check for warning log about container not available for network connection
    assert any(lvl == 'warning' and 'Container not available' in msg for (lvl, msg) in dummy.logged), (
        'Expected a warning log that container is not available to connect to network'
    )
