import os
import types
import builtins
import pytest

import openhands.runtime.impl.docker.docker_runtime as docker_runtime
from openhands.runtime.runtime_status import RuntimeStatus


class DummyContainer:
    pass


class DummyDeviceRequest:
    created = []

    def __init__(self, capabilities=None, count=None, device_ids=None):
        # record the parameters for assertions
        DummyDeviceRequest.created.append({
            "capabilities": capabilities,
            "count": count,
            "device_ids": device_ids,
        })


def make_fake_self(
    *,
    port_sequence,
    vscode_port=None,
    use_host_network=False,
    runtime_container_image="image",
    enable_gpu=False,
    cuda_visible_devices=None,
    volumes_return=None,
    config_debug=False,
    vscode_enabled=False,
):
    """
    Build a simple namespace object with attributes and methods expected by
    DockerRuntime.init_container so we can call the unbound function directly
    (DockerRuntime.init_container(self)).
    port_sequence: iterator or list of (port, lock) tuples returned in order
      for calls to _find_available_port_with_lock
    """
    port_iter = iter(port_sequence)

    logs = []
    statuses = []
    run_calls = []

    def log(level, message):
        logs.append((level, message))

    def set_runtime_status(status):
        statuses.append(status)

    def _find_available_port_with_lock(port_range):
        try:
            return next(port_iter)
        except StopIteration:
            # fallback deterministic value
            return (8000, None)

    def _process_volumes():
        return volumes_return

    def _process_overlay_mounts():
        # return something plausible
        return ["overlay-mount"]

    def get_action_execution_server_startup_command():
        return "run-server-cmd"

    class DummyContainers:
        def __init__(self):
            self._last_kwargs = None

        def run(self, *args, **kwargs):
            # store kwargs for assertions and return dummy container
            self._last_kwargs = kwargs
            run_calls.append(kwargs)
            return DummyContainer()

    docker_client = types.SimpleNamespace(containers=DummyContainers())

    sandbox = types.SimpleNamespace(
        vscode_port=vscode_port,
        local_runtime_url="http://localhost",
        use_host_network=use_host_network,
        runtime_binding_address="127.0.0.1",
        runtime_startup_env_vars={"STARTUP_KEY": "1"},
        enable_gpu=enable_gpu,
        cuda_visible_devices=cuda_visible_devices,
        docker_runtime_kwargs=None,
    )

    config = types.SimpleNamespace(
        sandbox=sandbox,
        debug=config_debug,
        workspace_base="/tmp/workspace",
        workspace_mount_path_in_sandbox="/openhands/workspace",
    )

    self = types.SimpleNamespace()
    # attributes used by init_container
    self.log = log
    self.set_runtime_status = set_runtime_status
    self._find_available_port_with_lock = _find_available_port_with_lock
    self.api_url = None
    self.initial_env_vars = {"FOO": "bar"}
    self.sid = "session-123"
    self.vscode_enabled = vscode_enabled
    self._process_volumes = _process_volumes
    self._process_overlay_mounts = _process_overlay_mounts
    self.get_action_execution_server_startup_command = (
        get_action_execution_server_startup_command
    )
    self.docker_client = docker_client
    self.runtime_container_image = runtime_container_image
    self.container_name = "container-xyz"
    self.config = config
    self.close_called = False

    def close():
        self.close_called = True

    self.close = close

    # placeholders to be set when method runs
    self._host_port = None
    self._host_port_lock = None
    self._container_port = None
    self._vscode_port = None
    self._vscode_port_lock = None
    self._app_ports = None
    self._app_port_locks = None
    self.container = None

    # expose captures for assertions
    self._captured = {
        "logs": logs,
        "statuses": statuses,
        "run_calls": run_calls,
        "docker_client": docker_client,
    }

    return self


@pytest.fixture(autouse=True)
def patch_device_request(monkeypatch):
    """Monkeypatch docker.types.DeviceRequest used by the implementation to our dummy.
    This avoids importing real docker SDK and makes instantiation observable.
    """
    # Ensure docker.types exists and patch DeviceRequest
    # If docker.types is not importable in the test environment, create a minimal shim
    try:
        import docker.types as docker_types
    except Exception:
        # create a fake docker.types module
        import types as _types

        docker_types = _types.SimpleNamespace()
        monkeypatch.setitem(sys.modules, "docker.types", docker_types)

    monkeypatch.setattr(docker_runtime.docker, "types", docker_runtime.docker.types, raising=False)
    # Patch the DeviceRequest class used in the module under test
    monkeypatch.setattr(docker_runtime.docker.types, "DeviceRequest", DummyDeviceRequest, raising=False)
    # Clear any previous records
    DummyDeviceRequest.created.clear()
    yield


def test_init_container_with_host_network_and_vscode_configured_round_006(monkeypatch):
    """Exercise the branch where use_host_network is True (host mode), a configured vscode_port exists,
    debug is enabled, DOCKER_HOST_ADDR is provided, and the container starts successfully.

    Assertions:
    - containers.run is called and container assigned
    - runtime status becomes RUNTIME_STARTED
    - run kwargs include network_mode 'host' and ports is None
    - environment passed contains DEBUG and DOCKER_HOST_ADDR and VSCODE_PORT
    """
    # Arrange: prepare port sequence: host port, (vscode not allocated because configured), app ports
    ports = [(50000, "lock-host"), (50001, "lock-app1"), (50002, "lock-app2")]

    # Set DOCKER_HOST_ADDR in env for this test
    monkeypatch.setenv("DOCKER_HOST_ADDR", "9.9.9.9")

    fake = make_fake_self(
        port_sequence=ports,
        vscode_port=1234,  # configured vscode port path
        use_host_network=True,
        runtime_container_image="img:latest",
        enable_gpu=False,
        volumes_return={"/some/path": {"bind": "/m", "mode": "rw"}},
        config_debug=True,
        vscode_enabled=True,
    )

    # Act
    # Call the unbound method with our fake object
    docker_runtime.DockerRuntime.init_container(fake)

    # Assert: container started and runtime status set
    assert isinstance(fake.container, DummyContainer)
    assert fake._captured["statuses"][-1] == RuntimeStatus.RUNTIME_STARTED

    # Inspect the call to containers.run
    run_calls = fake._captured["run_calls"]
    assert len(run_calls) == 1
    kwargs = run_calls[0]

    # network_mode should be 'host' and ports mapping should be None in host mode
    assert kwargs.get("network_mode") == "host"
    assert kwargs.get("ports") is None

    env = kwargs.get("environment")
    assert env is not None
    # DEBUG should be present because config.debug True
    assert env.get("DEBUG") == "true"
    # DOCKER_HOST_ADDR must have been passed through
    assert env.get("DOCKER_HOST_ADDR") == "9.9.9.9"
    # VSCODE_PORT should reflect configured value
    assert env.get("VSCODE_PORT") == str(1234)

    # cleanup env var
    monkeypatch.delenv("DOCKER_HOST_ADDR", raising=False)


def test_init_container_with_ports_and_gpu_and_no_image_raises_round_006(monkeypatch):
    """Exercise branch where vscode_port is not configured (so runtime finds one),
    GPU is enabled with no specific device ids (None) which should create a DeviceRequest with count=-1,
    and runtime_container_image is None which should raise ValueError and call close().

    Assertions:
    - DeviceRequest was instantiated with expected parameters
    - A ValueError is raised complaining about missing runtime_container_image
    - close() is called on the runtime object
    """
    # Arrange: sequence for ports: host port, vscode port, app_port1, app_port2
    ports = [(51000, "lock-host"), (51001, "lock-vscode"), (52001, "lock-a1"), (52002, "lock-a2")]

    # Ensure DOCKER_HOST_ADDR is not set
    monkeypatch.delenv("DOCKER_HOST_ADDR", raising=False)

    fake = make_fake_self(
        port_sequence=ports,
        vscode_port=None,  # triggers allocation path
        use_host_network=False,
        runtime_container_image=None,  # should cause ValueError in try block
        enable_gpu=True,
        cuda_visible_devices=None,  # triggers count=-1 branch
        volumes_return=None,  # trigger "no volumes" branch -> volumes = {}
        config_debug=False,
        vscode_enabled=False,
    )

    # Patch docker.types.DeviceRequest to our dummy to capture instantiation
    monkeypatch.setattr(docker_runtime.docker.types, "DeviceRequest", DummyDeviceRequest, raising=False)
    DummyDeviceRequest.created.clear()

    # Act & Assert: calling init_container should raise ValueError due to missing image
    with pytest.raises(ValueError) as excinfo:
        docker_runtime.DockerRuntime.init_container(fake)

    assert "Runtime container image is not set" in str(excinfo.value)

    # close() should have been called
    assert fake.close_called is True

    # DeviceRequest should have been created once (gpu enabled)
    assert len(DummyDeviceRequest.created) == 1
    entry = DummyDeviceRequest.created[0]
    # capabilities should include gpu
    assert entry["capabilities"] == [["gpu"]] or entry["capabilities"] == [["gpu"]]
    # count should be -1 for 'all' GPUs
    assert entry["count"] == -1
