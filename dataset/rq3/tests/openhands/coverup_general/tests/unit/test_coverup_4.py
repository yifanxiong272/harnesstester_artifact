# file: openhands/runtime/impl/docker/docker_runtime.py:398-555
# asked: {"lines": [399, 400, 403, 406, 409, 410, 411, 413, 414, 418, 419, 421, 422, 423, 426, 428, 429, 430, 434, 435, 436, 437, 438, 439, 440, 445, 446, 447, 448, 449, 453, 454, 455, 456, 457, 461, 462, 463, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 480, 481, 483, 484, 486, 488, 491, 494, 495, 496, 498, 499, 500, 501, 504, 505, 507, 508, 509, 510, 511, 514, 515, 516, 517, 521, 522, 523, 524, 526, 528, 529, 532, 533, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 554, 555], "branches": [[409, 410], [409, 413], [435, 436], [435, 461], [445, 446], [445, 453], [453, 454], [453, 467], [480, 481], [480, 483], [483, 484], [483, 486], [494, 495], [494, 499], [507, 508], [507, 521], [509, 510], [509, 514], [523, 524], [523, 526]]}
# gained: {"lines": [399, 400, 403, 406, 409, 410, 411, 413, 414, 418, 419, 421, 422, 423, 426, 428, 429, 430, 434, 435, 436, 437, 438, 439, 440, 445, 446, 447, 448, 449, 453, 454, 455, 456, 457, 461, 462, 463, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 480, 481, 483, 484, 486, 488, 491, 494, 495, 496, 498, 499, 500, 501, 504, 505, 507, 508, 509, 514, 515, 516, 517, 521, 522, 523, 524, 526, 528, 529, 532, 533, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 554, 555], "branches": [[409, 410], [409, 413], [435, 436], [435, 461], [445, 446], [453, 454], [453, 467], [480, 481], [480, 483], [483, 484], [483, 486], [494, 495], [494, 499], [507, 508], [507, 521], [509, 514], [523, 524], [523, 526]]}

import os
import types
import importlib
import pytest

from openhands.runtime.runtime_status import RuntimeStatus


def make_dummy_config(
    vscode_port=None,
    local_runtime_url="http://localhost",
    use_host_network=False,
    runtime_binding_address="127.0.0.1",
    workspace_base="/tmp/ws",
    workspace_mount_path_in_sandbox="/openhands/workspace",
    enable_gpu=False,
    cuda_visible_devices=None,
    runtime_startup_env_vars=None,
    docker_runtime_kwargs=None,
    base_container_image="base",
    runtime_container_image="runtime_img",
    runtime_extra_deps=None,
    debug=False,
):
    class Sandbox:
        pass

    sandbox = Sandbox()
    sandbox.vscode_port = vscode_port
    sandbox.local_runtime_url = local_runtime_url
    sandbox.use_host_network = use_host_network
    sandbox.runtime_binding_address = runtime_binding_address
    sandbox.enable_gpu = enable_gpu
    sandbox.cuda_visible_devices = cuda_visible_devices
    sandbox.runtime_startup_env_vars = runtime_startup_env_vars or {}
    sandbox.docker_runtime_kwargs = docker_runtime_kwargs or {}
    sandbox.base_container_image = base_container_image
    sandbox.runtime_container_image = runtime_container_image
    sandbox.runtime_extra_deps = runtime_extra_deps
    sandbox.local_runtime_url = local_runtime_url

    class Config:
        pass

    cfg = Config()
    cfg.sandbox = sandbox
    cfg.workspace_base = workspace_base
    cfg.workspace_mount_path_in_sandbox = workspace_mount_path_in_sandbox
    cfg.debug = debug
    return cfg


def _make_runtime_instance(module, config, sid="default-sid"):
    # Create instance without calling __init__ to avoid side-effects.
    DockerRuntime = getattr(module, "DockerRuntime")
    inst = object.__new__(DockerRuntime)
    # Minimal attributes used by init_container
    inst.config = config
    inst.sid = sid
    inst.initial_env_vars = {}
    inst.container = None
    inst.container_name = "container-" + sid
    inst._host_port = -1
    inst._container_port = -1
    inst._vscode_port = -1
    inst._app_ports = []
    inst._host_port_lock = None
    inst._vscode_port_lock = None
    inst._app_port_locks = []
    inst.api_url = ""
    inst.runtime_container_image = config.sandbox.runtime_container_image
    return inst


def test_init_container_success_non_host_network_with_vscode_and_gpu(monkeypatch):
    # Import module under test
    module = importlib.import_module("openhands.runtime.impl.docker.docker_runtime")

    # Prepare config with a configured vscode_port and GPU enabled
    cfg = make_dummy_config(
        vscode_port=22222,
        local_runtime_url="http://localhost",
        use_host_network=False,
        runtime_binding_address="127.0.0.1",
        enable_gpu=True,
        cuda_visible_devices="0,1",
        runtime_startup_env_vars={"X": "Y"},
        runtime_container_image="my-runtime-image",
        debug=True,
    )

    inst = _make_runtime_instance(module, cfg, sid="sid-success")
    # Mark vscode enabled attribute expected by property
    inst._vscode_enabled = True

    # Prepare sequence of ports to be returned by _find_available_port_with_lock:
    # host_port, app_port_1, app_port_2
    ports_sequence = [
        (8000, object()),  # host port
        (9001, object()),  # app port 1
        (9002, object()),  # app port 2
    ]

    def fake_find_available(port_range, max_attempts=5):
        return ports_sequence.pop(0)

    inst._find_available_port_with_lock = fake_find_available

    # Ensure get_action_execution_server_startup_command returns something
    inst.get_action_execution_server_startup_command = lambda: ["run-server"]

    # Process volumes -> non-empty to avoid empty-volumes branch
    inst._process_volumes = lambda: {"/host/ws": {"bind": "/openhands/code", "mode": "rw"}}
    inst._process_overlay_mounts = lambda: []

    # Provide a fake docker.types.DeviceRequest class in module docker
    class FakeDeviceRequest:
        def __init__(self, capabilities=None, count=None, device_ids=None):
            self.capabilities = capabilities
            self.count = count
            self.device_ids = device_ids

        def __repr__(self):
            return f"FakeDeviceRequest({self.capabilities},{self.count},{self.device_ids})"

    # Ensure docker.types exists on the imported docker in module
    if not hasattr(module.docker, "types"):
        module.docker.types = types.SimpleNamespace()
    monkeypatch.setattr(module.docker.types, "DeviceRequest", FakeDeviceRequest, raising=False)

    # Prepare a fake docker client that records the run kwargs and returns a fake container
    recorded = {}

    class FakeContainer:
        pass

    class FakeContainers:
        def run(self, image, init, command, entrypoint, network_mode, ports, working_dir, name, detach, environment, volumes, mounts, device_requests, **kwargs):
            recorded.update(
                dict(
                    image=image,
                    init=init,
                    command=command,
                    entrypoint=entrypoint,
                    network_mode=network_mode,
                    ports=ports,
                    working_dir=working_dir,
                    name=name,
                    detach=detach,
                    environment=environment,
                    volumes=volumes,
                    mounts=mounts,
                    device_requests=device_requests,
                    extra_kwargs=kwargs,
                )
            )
            # Also set container on instance to mimic real behavior
            inst.container = FakeContainer()
            return inst.container

    fake_docker_client = types.SimpleNamespace(containers=FakeContainers())
    inst.docker_client = fake_docker_client

    # Capture runtime status changes
    statuses = []

    def fake_set_runtime_status(s):
        statuses.append(s)

    inst.set_runtime_status = fake_set_runtime_status

    # Simple logger that records messages
    logs = []

    def fake_log(level, message):
        logs.append((level, message))

    inst.log = fake_log

    # Provide DOCKER_HOST_ADDR env var
    monkeypatch.setenv("DOCKER_HOST_ADDR", "9.8.7.6")

    # Run init_container
    inst.init_container()

    # Assertions: container set, device_requests created for GPUs, and env vars include values
    assert isinstance(inst.container, FakeContainer)
    assert statuses[0] == RuntimeStatus.STARTING_RUNTIME
    assert statuses[-1] == RuntimeStatus.RUNTIME_STARTED
    # Check that recorded run used our image
    assert recorded["image"] == "my-runtime-image"
    # Device requests should be a list with FakeDeviceRequest
    dr = recorded["device_requests"]
    assert isinstance(dr, list) and isinstance(dr[0], FakeDeviceRequest)
    assert dr[0].capabilities == [["gpu"]]
    # Environment contains VSCODE_PORT, APP_PORT_1 and APP_PORT_2 and DOCKER_HOST_ADDR and DEBUG
    env = recorded["environment"]
    assert env["VSCODE_PORT"] == str(cfg.sandbox.vscode_port)
    assert env["APP_PORT_1"] == "9001"
    assert env["APP_PORT_2"] == "9002"
    assert env["DOCKER_HOST_ADDR"] == "9.8.7.6"
    assert env["DEBUG"] == "true"
    # Ports mapping should include container port mapping to host port
    assert f"{inst._container_port}/tcp" in recorded["ports"]


def test_init_container_runtime_image_none_raises_and_close_called(monkeypatch):
    # Import module under test
    module = importlib.import_module("openhands.runtime.impl.docker.docker_runtime")

    # Prepare config with host network enabled and no runtime image (None)
    cfg = make_dummy_config(
        vscode_port=None,
        local_runtime_url="http://localhost",
        use_host_network=True,
        runtime_binding_address="127.0.0.1",
        enable_gpu=False,
        runtime_container_image=None,
    )

    inst = _make_runtime_instance(module, cfg, sid="sid-fail")
    # Mark vscode disabled attribute expected by property
    inst._vscode_enabled = False

    # _find_available_port_with_lock will be called four times: host, vscode, app1, app2
    seq = [
        (7000, object()),  # host port
        (2222, object()),  # vscode port
        (8001, object()),  # app1
        (8002, object()),  # app2
    ]

    def fake_find_available(port_range, max_attempts=5):
        return seq.pop(0)

    inst._find_available_port_with_lock = fake_find_available

    # volumes processing - return empty to trigger logger.debug branch (uses module logger)
    inst._process_volumes = lambda: {}
    inst._process_overlay_mounts = lambda: []

    # Ensure get_action_execution_server_startup_command does not access unknown attributes
    inst.get_action_execution_server_startup_command = lambda: ["run-server"]

    # Capture runtime status changes
    statuses = []

    def fake_set_runtime_status(s):
        statuses.append(s)

    inst.set_runtime_status = fake_set_runtime_status

    # Capture close call
    closed = {"called": False}

    def fake_close():
        closed["called"] = True

    inst.close = fake_close

    # Capture logs
    logs = []

    def fake_log(level, message):
        logs.append((level, message))

    inst.log = fake_log

    # Now call init_container and expect ValueError to be raised and close called
    with pytest.raises(ValueError):
        inst.init_container()

    # Ensure STARTING_RUNTIME was set before failure
    assert statuses and statuses[0] == RuntimeStatus.STARTING_RUNTIME
    # Ensure close was called by except clause
    assert closed["called"] is True
    # Because use_host_network True, a warning about host network should be logged via inst.log
    warn_msgs = [m for (lvl, m) in logs if lvl == "warn"]
    assert any("host network mode" in m for m in warn_msgs)
