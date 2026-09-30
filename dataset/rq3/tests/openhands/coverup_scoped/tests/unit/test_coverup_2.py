# file: openhands/runtime/impl/docker/docker_runtime.py:398-555
# asked: {"lines": [399, 400, 403, 406, 409, 410, 411, 413, 414, 418, 419, 421, 422, 423, 426, 428, 429, 430, 434, 435, 436, 437, 438, 439, 440, 445, 446, 447, 448, 449, 453, 454, 455, 456, 457, 461, 462, 463, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 480, 481, 483, 484, 486, 488, 491, 494, 495, 496, 498, 499, 500, 501, 504, 505, 507, 508, 509, 510, 511, 514, 515, 516, 517, 521, 522, 523, 524, 526, 528, 529, 532, 533, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 554, 555], "branches": [[409, 410], [409, 413], [435, 436], [435, 461], [445, 446], [445, 453], [453, 454], [453, 467], [480, 481], [480, 483], [483, 484], [483, 486], [494, 495], [494, 499], [507, 508], [507, 521], [509, 510], [509, 514], [523, 524], [523, 526]]}
# gained: {"lines": [399, 400, 403, 406, 409, 410, 411, 413, 414, 418, 419, 421, 422, 423, 426, 428, 429, 430, 434, 435, 436, 437, 438, 439, 440, 445, 446, 447, 448, 449, 453, 454, 455, 456, 457, 461, 462, 463, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 480, 483, 486, 488, 491, 494, 495, 496, 498, 499, 500, 501, 504, 505, 507, 508, 509, 510, 511, 521, 522, 523, 524, 526, 528, 529, 532, 533, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 554, 555], "branches": [[409, 410], [409, 413], [435, 436], [435, 461], [445, 446], [453, 454], [453, 467], [480, 483], [483, 486], [494, 495], [507, 508], [507, 521], [509, 510], [523, 524], [523, 526]]}

import pytest
from types import SimpleNamespace

from openhands.runtime.impl.docker.docker_runtime import DockerRuntime
from openhands.runtime.runtime_status import RuntimeStatus
import docker


def _make_dummy_device_request_class():
    class DummyDeviceRequest:
        def __init__(self, capabilities=None, count=None, device_ids=None):
            # store the parameters for inspection
            self.capabilities = capabilities
            self.count = count
            self.device_ids = device_ids

        def __repr__(self):
            return f"DummyDeviceRequest(capabilities={self.capabilities}, count={self.count}, device_ids={self.device_ids})"

    return DummyDeviceRequest


def _make_docker_client_mock(captured):
    class DummyContainers:
        def run(self, image, init, command, entrypoint, network_mode, ports, working_dir, name, detach, environment, volumes, mounts, device_requests, **kwargs):
            # capture arguments for assertions
            captured['image'] = image
            captured['init'] = init
            captured['command'] = command
            captured['entrypoint'] = entrypoint
            captured['network_mode'] = network_mode
            captured['ports'] = ports
            captured['working_dir'] = working_dir
            captured['name'] = name
            captured['detach'] = detach
            captured['environment'] = environment
            captured['volumes'] = volumes
            captured['mounts'] = mounts
            captured['device_requests'] = device_requests
            captured['kwargs'] = kwargs
            # return a dummy container object
            return SimpleNamespace(id="dummy", short_id="dumm", attrs={})

    class DummyDockerClient:
        def __init__(self):
            self.containers = DummyContainers()

    return DummyDockerClient()


def _setup_instance(monkeypatch, port_sequence, config_sandbox: SimpleNamespace, runtime_image, enable_vscode=True):
    # Prevent original __init__ from running
    monkeypatch.setattr(DockerRuntime, "__init__", lambda self, *a, **k: None)

    inst = DockerRuntime(None, None, None)  # __init__ is patched to do nothing

    # Replace vscode_enabled property on class with simple attribute value
    # Use raising=False to allow overwriting if property exists
    monkeypatch.setattr(DockerRuntime, "vscode_enabled", enable_vscode, raising=False)

    # logging capture
    logs = []
    inst.log = lambda level, msg: logs.append((level, msg))
    inst.set_runtime_status = lambda status: setattr(inst, "_last_status", status)

    # port allocation function will pop from the provided sequence
    seq = list(port_sequence)

    def _find_available_port_with_lock(port_range, max_attempts=5):
        if not seq:
            raise RuntimeError("No more ports in sequence")
        p = seq.pop(0)
        # return a dummy lock object
        lock = SimpleNamespace(released=False)
        return p, lock

    inst._find_available_port_with_lock = _find_available_port_with_lock

    # config and sandbox
    inst.config = SimpleNamespace()
    inst.config.sandbox = config_sandbox
    inst.config.debug = False

    # Provide workspace attributes on config (code expects them on config, not sandbox)
    inst.config.workspace_base = getattr(config_sandbox, "workspace_base", "/tmp")
    inst.config.workspace_mount_path_in_sandbox = getattr(config_sandbox, "workspace_mount_path_in_sandbox", "/sandbox")

    # other attributes / stubs
    inst.initial_env_vars = {}
    inst.sid = "test-sid"
    inst.container_name = "test-container"
    inst._process_volumes = lambda: {}
    inst._process_overlay_mounts = lambda: []
    inst.get_action_execution_server_startup_command = lambda: ["run-server"]
    inst._app_ports = []
    inst._app_port_locks = []
    inst._host_port_lock = None
    inst._vscode_port_lock = None

    # runtime image
    inst.runtime_container_image = runtime_image

    return inst, logs


def test_init_container_success_non_host_network_with_vscode_and_gpu(monkeypatch):
    # Setup config sandbox
    sandbox = SimpleNamespace()
    sandbox.vscode_port = 7001  # configured vscode port should be used (no lock)
    sandbox.local_runtime_url = "http://localhost"
    sandbox.use_host_network = False
    sandbox.runtime_binding_address = "127.0.0.1"
    sandbox.workspace_base = "/base"
    sandbox.workspace_mount_path_in_sandbox = "/sandbox"
    sandbox.enable_gpu = True
    sandbox.cuda_visible_devices = None  # triggers count = -1 branch
    sandbox.docker_runtime_kwargs = {}
    sandbox.runtime_startup_env_vars = {}

    # Ports to be returned: host port, app_port_1, app_port_2
    port_seq = [5000, 6001, 6002]

    # Prepare instance
    captured = {}
    inst, logs = _setup_instance(monkeypatch, port_seq, sandbox, runtime_image="my-image", enable_vscode=True)

    # Provide a fake docker client; capture run args
    monkeypatch.setattr(docker.types, "DeviceRequest", _make_dummy_device_request_class())
    inst.docker_client = _make_docker_client_mock(captured)

    # Call the method under test
    inst.init_container()

    # Assertions
    # Container object should be set (returned dummy container)
    assert hasattr(inst, "container")
    assert inst.container is not None

    # runtime status should have been set to RUNTIME_STARTED
    assert getattr(inst, "_last_status", None) == RuntimeStatus.RUNTIME_STARTED

    # Check captured docker run parameters
    assert captured["image"] == "my-image"
    assert captured["command"] == ["run-server"]
    # ports mapping should include container port mapping and vscode and app ports
    ports = captured["ports"]
    assert ports is not None
    # container port assigned equals host port because code sets self._container_port = self._host_port
    assert f"{inst._container_port}/tcp" in ports
    # VSCODE port mapping exists and equals configured port
    assert f"{inst._vscode_port}/tcp" in ports
    # App ports present
    for p in inst._app_ports:
        assert f"{p}/tcp" in ports

    # Device requests should be present and indicate count -1 from cuda_visible_devices=None
    dr = captured["device_requests"]
    assert isinstance(dr, list)
    assert len(dr) == 1
    assert getattr(dr[0], "count", None) == -1
    assert getattr(dr[0], "capabilities", None) == [["gpu"]]


def test_init_container_failure_host_network_and_runtime_image_missing(monkeypatch):
    # Setup config sandbox for host network case
    sandbox = SimpleNamespace()
    sandbox.vscode_port = None  # will cause _find_available_port_with_lock to be called for vscode
    sandbox.local_runtime_url = "http://localhost"
    sandbox.use_host_network = True
    sandbox.runtime_binding_address = "127.0.0.1"
    sandbox.workspace_base = "/base"
    sandbox.workspace_mount_path_in_sandbox = "/sandbox"
    sandbox.enable_gpu = False
    sandbox.cuda_visible_devices = None
    sandbox.docker_runtime_kwargs = {}
    sandbox.runtime_startup_env_vars = {}

    # Ports sequence: host, vscode, app1, app2
    port_seq = [5100, 5101, 6101, 6102]

    # Prepare instance with runtime_container_image = None to trigger ValueError
    inst, logs = _setup_instance(monkeypatch, port_seq, sandbox, runtime_image=None, enable_vscode=False)

    # Provide a fake docker client that would raise if called (should not be called due to runtime image None)
    captured = {}
    inst.docker_client = _make_docker_client_mock(captured)

    # Track close being called
    closed = {"called": False}

    def fake_close(rm_all_containers=None):
        closed["called"] = True

    inst.close = fake_close

    # Call and expect the ValueError to be raised and close called
    with pytest.raises(ValueError):
        inst.init_container()

    assert closed["called"] is True

    # Since use_host_network=True, ensure a warning log was emitted during init_container
    assert any(level == "warn" for level, _ in logs)
