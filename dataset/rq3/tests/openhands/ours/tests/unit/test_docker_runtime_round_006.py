import os
from types import SimpleNamespace
import pytest

import openhands.runtime.impl.docker.docker_runtime as dr


class _DummyDeviceRequest:
    def __init__(self, *args, **kwargs):
        # store values so tests can verify the constructor was called
        self.args = args
        self.kwargs = kwargs


def _make_instance():
    # Create instance without calling __init__ to avoid heavy setup
    inst = dr.DockerRuntime.__new__(dr.DockerRuntime)
    # Provide no-op logging and state setters so init_container can call them
    inst._log_calls = []

    def _log(level, msg):
        inst._log_calls.append((level, msg))

    inst.log = _log
    inst._status_calls = []

    def _set_status(s):
        inst._status_calls.append(s)

    inst.set_runtime_status = _set_status
    return inst


def test_init_container_success_with_configured_vscode_and_gpu_none_round_006(monkeypatch):
    """
    Covers branches:
    - configured vscode_port path (409->410)
    - not using host network (435->436)
    - adding DOCKER_HOST_ADDR to environment (483->484)
    - enable_gpu True with cuda_visible_devices None -> DeviceRequest(count=-1) branch (509->510)
    - non-empty volumes truthy branch (494 not taken)
    - successful container start path and status set (547->548->549)
    """
    # Ensure global DEBUG flag does not interfere
    monkeypatch.setattr(dr, 'DEBUG', False)

    inst = _make_instance()

    # Prepare a sandboxed config where vscode_port is configured
    sandbox = SimpleNamespace(
        vscode_port=12345,
        local_runtime_url='http://127.0.0.1',
        runtime_binding_address='127.0.0.1',
        use_host_network=False,
        enable_gpu=True,
        cuda_visible_devices=None,
        runtime_startup_env_vars={'RUNTIME_KEY': 'RUNTIME_VAL'},
        docker_runtime_kwargs={'labels': {'k': 'v'}},
    )
    inst.config = SimpleNamespace(sandbox=sandbox, debug=False, workspace_base='/tmp', workspace_mount_path_in_sandbox='/sandbox')

    # Basic fields expected by init_container
    inst.initial_env_vars = {'INIT_A': '1'}
    inst.sid = 'SOME_SESSION'
    inst.runtime_container_image = 'my-image:latest'
    inst.container_name = 'test-container'

    # Patch the class attribute to avoid assigning to a read-only property
    monkeypatch.setattr(dr.DockerRuntime, 'vscode_enabled', True, raising=False)

    # Provide a deterministic sequence of ports for _find_available_port_with_lock
    ports = iter([(8000, 'lock_exec'), (9001, 'lock_app1'), (9002, 'lock_app2')])

    def fake_find_available_port_with_lock(_range):
        return next(ports)

    inst._find_available_port_with_lock = fake_find_available_port_with_lock

    # Provide non-empty volumes so the "if not volumes" branch is NOT taken
    inst._process_volumes = lambda: {'/host/path': {'bind': '/sandbox', 'mode': 'rw'}}
    inst._process_overlay_mounts = lambda: []
    inst.get_action_execution_server_startup_command = lambda: ['run-server']

    # Patch DeviceRequest so constructing it is safe and inspectable
    monkeypatch.setattr(dr.docker.types, 'DeviceRequest', _DummyDeviceRequest)

    # Ensure DOCKER_HOST_ADDR is present in environment to test branch
    monkeypatch.setenv('DOCKER_HOST_ADDR', '192.0.2.1')

    # Capture the docker run call
    run_calls = {}

    def fake_run(image, *args, **kwargs):
        run_calls['image'] = image
        run_calls['kwargs'] = kwargs
        # return a simple object representing the started container
        return SimpleNamespace(id='container-xyz')

    inst.docker_client = SimpleNamespace(containers=SimpleNamespace(run=fake_run))

    # Execute
    inst.init_container()

    # Assertions: container started and status was set to RUNTIME_STARTED
    assert hasattr(inst, 'container') and getattr(inst.container, 'id') == 'container-xyz'
    assert dr.RuntimeStatus.RUNTIME_STARTED in inst._status_calls

    # api_url should be constructed from sandbox.local_runtime_url and allocated container port
    # _find_available_port_with_lock returned 8000 as first value -> container_port == 8000
    assert inst.api_url == 'http://127.0.0.1:8000'

    # Verify docker.run was called with our image and environment populated
    assert run_calls.get('image') == 'my-image:latest'
    env = run_calls['kwargs']['environment']
    # keys created by init_container
    assert env['VSCODE_PORT'] == str(12345)
    assert env['APP_PORT_1'] == str(9001)
    assert env['APP_PORT_2'] == str(9002)
    # DOCKER_HOST_ADDR should have been propagated
    assert env['DOCKER_HOST_ADDR'] == '192.0.2.1'
    # Device requests should be present and use our DummyDeviceRequest
    dr_requests = run_calls['kwargs'].get('device_requests')
    assert isinstance(dr_requests, list) and isinstance(dr_requests[0], _DummyDeviceRequest)


def test_init_container_runtime_image_none_raises_round_006(monkeypatch):
    """
    Covers branches:
    - not configured vscode_port path (413->414) when none is provided
    - use_host_network True branch that logs a warning (461->464)
    - volumes falsy branch -> set to empty dict (494->499)
    - runtime_container_image None raising ValueError and triggering close() in except (523->525 -> 554->555)
    """
    monkeypatch.setattr(dr, 'DEBUG', False)

    inst = _make_instance()

    # sandbox where vscode_port is not configured and host network is used
    sandbox = SimpleNamespace(
        vscode_port=None,
        local_runtime_url='http://localhost',
        runtime_binding_address='127.0.0.1',
        use_host_network=True,
        enable_gpu=False,
        cuda_visible_devices=None,
        runtime_startup_env_vars={},
        docker_runtime_kwargs=None,
    )
    inst.config = SimpleNamespace(sandbox=sandbox, debug=False, workspace_base='/tmp', workspace_mount_path_in_sandbox='/sandbox')

    inst.initial_env_vars = {}
    inst.sid = 'SID'
    inst.runtime_container_image = None  # triggers the ValueError path
    inst.container_name = 'will-fail'

    # Patch the class attribute to avoid assigning to a read-only property
    monkeypatch.setattr(dr.DockerRuntime, 'vscode_enabled', False, raising=False)

    # Make _find_available_port_with_lock yield enough ports (exec, vscode, app1, app2)
    ports = iter([(8010, 'lock_exec'), (12345, 'lock_vscode'), (9101, 'lock_app1'), (9102, 'lock_app2')])

    def fake_find_available_port_with_lock(_range):
        return next(ports)

    inst._find_available_port_with_lock = fake_find_available_port_with_lock

    # _process_volumes returns falsy to force the volumes = {} branch
    inst._process_volumes = lambda: None

    # Track whether close() is called in the exception handler
    called = {'close': False}

    def fake_close():
        called['close'] = True

    inst.close = fake_close

    # runtime_container_image is None -> should raise ValueError and call close()
    with pytest.raises(ValueError):
        inst.init_container()

    assert called['close'] is True
