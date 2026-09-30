import inspect
import types
import pytest
import asyncio

import importlib


dr = importlib.import_module('openhands.runtime.impl.docker.docker_runtime')

# Helper async wrapper that runs sync functions or awaits coroutines deterministically
async def _sync_runner(fn, *a, **kw):
    res = fn(*a, **kw)
    if inspect.isawaitable(res):
        return await res
    return res

class DummyLogStreamer:
    def __init__(self, container, log_fn):
        self.container = container
        self.log_fn = log_fn


class CustomNotFound(Exception):
    pass


class CustomDisconnected(Exception):
    pass


@pytest.mark.asyncio
async def test_connect_attach_existing_notfound_round_018(monkeypatch):
    """
    Simulate _attach_to_container raising docker.errors.NotFound while attach_to_existing=True.
    Expect an AgentRuntimeDisconnectedError (patched to CustomDisconnected) to be raised,
    and that the initial STARTING_RUNTIME status call and warning log about missing container are produced.
    """
    # Patch module-level dependencies deterministically
    monkeypatch.setattr(dr, 'call_sync_from_async', _sync_runner)
    monkeypatch.setattr(dr, 'LogStreamer', DummyLogStreamer)
    # Ensure docker.errors.NotFound exists in module and is our CustomNotFound
    if not hasattr(dr, 'docker'):
        dr.docker = types.SimpleNamespace()
    if not hasattr(dr.docker, 'errors'):
        dr.docker.errors = types.SimpleNamespace()
    dr.docker.errors.NotFound = CustomNotFound
    # Patch the AgentRuntimeDisconnectedError to a deterministic class we can catch
    dr.AgentRuntimeDisconnectedError = CustomDisconnected

    statuses = []
    logs = []

    # Fake self object with only attributes used in connect
    def set_runtime_status(s):
        statuses.append(s)

    def log(level, msg):
        logs.append((level, msg))

    def _attach_to_container():
        raise dr.docker.errors.NotFound('no container')

    fake_self = types.SimpleNamespace(
        set_runtime_status=set_runtime_status,
        _attach_to_container=_attach_to_container,
        attach_to_existing=True,
        container_name='con-xyz',
        log=log,
    )

    with pytest.raises(CustomDisconnected):
        await dr.DockerRuntime.connect(fake_self)

    # Assertions: starting runtime status set, and a warning log about missing container recorded
    assert statuses == [dr.RuntimeStatus.STARTING_RUNTIME]
    assert any(l == 'warning' and 'Container con-xyz not found.' in m for l, m in logs)


@pytest.mark.asyncio
async def test_connect_attach_build_and_logstreamer_round_018(monkeypatch):
    """
    Simulate the NotFound path with attach_to_existing=False and DEBUG_RUNTIME True
    such that LogStreamer is created and the runtime goes to READY and setup_initial_env is called.
    """
    monkeypatch.setattr(dr, 'call_sync_from_async', _sync_runner)
    monkeypatch.setattr(dr, 'LogStreamer', DummyLogStreamer)
    # Ensure docker.errors.NotFound exists
    if not hasattr(dr, 'docker'):
        dr.docker = types.SimpleNamespace()
    if not hasattr(dr.docker, 'errors'):
        dr.docker.errors = types.SimpleNamespace()
    dr.docker.errors.NotFound = CustomNotFound
    # Keep AgentRuntimeDisconnectedError as original or patch harmlessly if missing
    dr.AgentRuntimeDisconnectedError = CustomDisconnected

    # Turn on DEBUG_RUNTIME for this test
    monkeypatch.setattr(dr, 'DEBUG_RUNTIME', True)

    statuses = []
    logs = []
    calls = {
        'maybe_built': False,
        'init_called': False,
        'wait_called': False,
        'setup_called': False,
    }

    def set_runtime_status(s):
        statuses.append(s)

    def log(level, msg):
        logs.append((level, msg))

    def _attach_to_container():
        raise dr.docker.errors.NotFound('no container')

    def maybe_build_runtime_container_image():
        calls['maybe_built'] = True

    def init_container():
        calls['init_called'] = True

    def wait_until_alive():
        calls['wait_called'] = True

    def setup_initial_env():
        calls['setup_called'] = True

    # container present (truthy) to trigger LogStreamer instantiation path
    fake_container = object()
    # Provide a small plugin list used in debug message
    fake_plugins = [types.SimpleNamespace(name='plug1')]

    fake_self = types.SimpleNamespace(
        set_runtime_status=set_runtime_status,
        _attach_to_container=_attach_to_container,
        attach_to_existing=False,
        container_name='con-abc',
        runtime_container_image='img:latest',
        maybe_build_runtime_container_image=maybe_build_runtime_container_image,
        log=log,
        init_container=init_container,
        container=fake_container,
        vscode_url='http://vscode',
        plugins=fake_plugins,
        api_url='http://api',
        wait_until_alive=wait_until_alive,
        setup_initial_env=setup_initial_env,
        config=types.SimpleNamespace(sandbox=types.SimpleNamespace(additional_networks=[])),
        docker_client=types.SimpleNamespace(networks=types.SimpleNamespace(get=lambda n: None)),
        _runtime_initialized=False,
    )

    await dr.DockerRuntime.connect(fake_self)

    # LogStreamer should be attached because DEBUG_RUNTIME True and container truthy
    assert isinstance(fake_self.log_streamer, DummyLogStreamer)
    # Build, init, wait and setup should have been called
    assert calls['maybe_built'] is True
    assert calls['init_called'] is True
    assert calls['wait_called'] is True
    assert calls['setup_called'] is True
    # Runtime statuses should include initial STARTING_RUNTIME and final READY
    assert dr.RuntimeStatus.STARTING_RUNTIME in statuses
    assert dr.RuntimeStatus.READY in statuses
    # runtime marked initialized
    assert fake_self._runtime_initialized is True
    # 'Runtime is ready.' info should be logged
    assert any(l == 'info' and 'Runtime is ready.' in m for l, m in logs)
    # debug log should include plugin name
    assert any(l == 'debug' and 'plug1' in m for l, m in logs)


@pytest.mark.asyncio
async def test_connect_network_exception_round_018(monkeypatch):
    """
    Simulate network connection failure during the additional_networks loop
    to exercise the exception logging branch.
    """
    monkeypatch.setattr(dr, 'call_sync_from_async', _sync_runner)
    monkeypatch.setattr(dr, 'LogStreamer', DummyLogStreamer)
    # Ensure docker.errors.NotFound exists
    if not hasattr(dr, 'docker'):
        dr.docker = types.SimpleNamespace()
    if not hasattr(dr.docker, 'errors'):
        dr.docker.errors = types.SimpleNamespace()
    dr.docker.errors.NotFound = CustomNotFound
    dr.AgentRuntimeDisconnectedError = CustomDisconnected

    logs = []

    def set_runtime_status(s):
        pass

    def log(level, msg):
        logs.append((level, msg))

    def _attach_to_container():
        raise dr.docker.errors.NotFound('no container')

    def init_container():
        # mark container started (but we keep container None to trigger network log path)
        return None

    def wait_until_alive():
        return None

    def setup_initial_env():
        return None

    # Simulate docker_client.networks.get raising an error
    def networks_get(name):
        raise Exception('network-boom')

    fake_self = types.SimpleNamespace(
        set_runtime_status=set_runtime_status,
        _attach_to_container=_attach_to_container,
        attach_to_existing=False,
        container_name='con-net',
        runtime_container_image='img:net',
        maybe_build_runtime_container_image=lambda: None,
        log=log,
        init_container=init_container,
        container=None,  # No container to force the 'Container not available' path if not for exception
        vscode_url='http://vscode',
        plugins=[],
        api_url='http://api',
        wait_until_alive=wait_until_alive,
        setup_initial_env=setup_initial_env,
        config=types.SimpleNamespace(sandbox=types.SimpleNamespace(additional_networks=['sandbox-net'])),
        docker_client=types.SimpleNamespace(networks=types.SimpleNamespace(get=networks_get)),
        _runtime_initialized=False,
    )

    # Run connect; no exception should escape for network errors
    await dr.DockerRuntime.connect(fake_self)

    # Expect an error log about failing to connect instance to network and the exception message logged
    assert any(l == 'error' and 'Failed to connect instance con-net to network sandbox-net' in m for l, m in logs)
    assert any(l == 'error' and 'network-boom' in m for l, m in logs)
