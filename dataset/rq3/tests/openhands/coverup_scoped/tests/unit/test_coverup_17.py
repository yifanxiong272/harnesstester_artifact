# file: openhands/runtime/impl/docker/docker_runtime.py:177-238
# asked: {"lines": [178, 179, 180, 181, 182, 183, 184, 185, 187, 188, 189, 190, 192, 193, 194, 195, 198, 199, 201, 203, 204, 205, 207, 209, 210, 212, 213, 215, 216, 217, 219, 220, 221, 223, 224, 225, 226, 227, 229, 230, 231, 233, 234, 235, 236, 238], "branches": [[182, 183], [182, 188], [198, 199], [198, 201], [203, 204], [203, 207], [209, 210], [209, 212], [212, 213], [212, 215], [219, 220], [219, 221], [223, 0], [223, 224], [226, 227], [226, 229]]}
# gained: {"lines": [178, 179, 180, 181, 182, 183, 184, 185, 187, 188, 189, 190, 192, 193, 194, 195, 198, 199, 203, 204, 205, 207, 209, 210, 212, 213, 215, 216, 217, 219, 220, 221, 223, 224, 225, 226, 227, 233, 234, 235, 236, 238], "branches": [[182, 183], [182, 188], [198, 199], [203, 204], [209, 210], [212, 213], [219, 220], [223, 0], [223, 224], [226, 227]]}

import types
import pytest

import openhands.runtime.impl.docker.docker_runtime as drmod
from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.runtime.runtime_status import RuntimeStatus

# Ensure call_sync_from_async is deterministic for tests (just call the sync function)
@pytest.fixture(autouse=True)
def patch_call_sync_from_async(monkeypatch):
    async def _call_sync_from_async(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(drmod, "call_sync_from_async", _call_sync_from_async)
    yield


@pytest.mark.asyncio
async def test_connect_attach_to_existing_not_found_raises(monkeypatch):
    """
    When _attach_to_container raises docker.errors.NotFound and attach_to_existing is True,
    connect should log a warning and raise AgentRuntimeDisconnectedError.
    """
    # Prepare a bare DockerRuntime instance without running its __init__
    inst = drmod.DockerRuntime.__new__(drmod.DockerRuntime)

    # Track statuses and logs
    statuses = []
    logs = []

    def set_runtime_status(s):
        statuses.append(s)

    def log(level, message):
        logs.append((level, message))

    # Make _attach_to_container raise NotFound synchronously
    def _attach_to_container():
        if hasattr(drmod.docker, "errors") and hasattr(drmod.docker.errors, "NotFound"):
            raise drmod.docker.errors.NotFound("not found for test")
        raise Exception("not found for test")

    # Assign attributes required by connect (avoid setting readonly properties like vscode_url)
    inst._attach_to_container = _attach_to_container
    inst.attach_to_existing = True
    inst.container_name = "test_container"
    inst.container = None
    inst.runtime_container_image = "img"
    inst.api_url = "http://api"
    inst.plugins = []
    inst.config = types.SimpleNamespace(sandbox=types.SimpleNamespace(additional_networks=[]))
    inst.docker_client = types.SimpleNamespace(networks=types.SimpleNamespace(get=lambda n: None))
    inst.set_runtime_status = set_runtime_status
    inst.log = log
    inst._runtime_initialized = False
    # ensure vscode properties referenced by connect/get_vscode_token are present
    inst._vscode_enabled = False
    inst._vscode_token = None

    # Ensure DEBUG_RUNTIME doesn't affect this test path
    monkeypatch.setattr(drmod, "DEBUG_RUNTIME", False)

    with pytest.raises(AgentRuntimeDisconnectedError):
        await inst.connect()

    # Verify that the runtime status was set to STARTING_RUNTIME at least once
    assert RuntimeStatus.STARTING_RUNTIME in statuses

    # Verify warning log about container not found
    assert any("Container test_container not found." in msg for _, msg in logs)


@pytest.mark.asyncio
async def test_connect_creates_container_and_handles_networks_and_log_streamer(monkeypatch):
    """
    When _attach_to_container raises NotFound and attach_to_existing is False,
    connect should build/start container, call init_container, wait_until_alive, setup_initial_env,
    set READY status, set _runtime_initialized True, create LogStreamer if DEBUG_RUNTIME True,
    and handle network connect success and exceptions with appropriate logs.
    """
    inst = drmod.DockerRuntime.__new__(drmod.DockerRuntime)

    statuses = []
    logs = []

    def set_runtime_status(s):
        statuses.append(s)

    def log(level, message):
        logs.append((level, message))

    # _attach_to_container will raise NotFound to trigger creation path
    def _attach_to_container():
        if hasattr(drmod.docker, "errors") and hasattr(drmod.docker.errors, "NotFound"):
            raise drmod.docker.errors.NotFound("not found for create path")
        raise Exception("not found for create path")

    # maybe_build_runtime_container_image should be recorded as called
    called_mb = {"called": False}

    def maybe_build_runtime_container_image():
        called_mb["called"] = True

    # init_container should set container to a truthy object (avoid setting readonly props)
    def init_container():
        inst.container = object()

    # wait_until_alive and setup_initial_env are called via call_sync_from_async
    def wait_until_alive():
        return None

    setup_called = []

    def setup_initial_env():
        setup_called.append(True)

    # Prepare networks: one good network, one that raises on get
    network_connected = []

    class GoodNetwork:
        def connect(self, container):
            network_connected.append(("connected", container))

    def networks_get(name):
        if name == "badnet":
            raise RuntimeError("network lookup failed")
        return GoodNetwork()

    docker_client = types.SimpleNamespace(networks=types.SimpleNamespace(get=networks_get))

    # Replace LogStreamer with dummy to avoid side effects
    created_logstreamers = []

    class DummyLogStreamer:
        def __init__(self, container, log_fn):
            created_logstreamers.append((container, log_fn))

    monkeypatch.setattr(drmod, "LogStreamer", DummyLogStreamer)
    # Ensure DEBUG_RUNTIME True for this test
    monkeypatch.setattr(drmod, "DEBUG_RUNTIME", True)

    inst._attach_to_container = _attach_to_container
    inst.maybe_build_runtime_container_image = maybe_build_runtime_container_image
    inst.init_container = init_container
    inst.wait_until_alive = wait_until_alive
    inst.setup_initial_env = setup_initial_env
    inst.attach_to_existing = False
    inst.container_name = "created_container"
    inst.container = None  # will be set by init_container
    inst.runtime_container_image = "img_created"
    inst.api_url = "http://api"
    inst.plugins = [types.SimpleNamespace(name="p1"), types.SimpleNamespace(name="p2")]
    inst.config = types.SimpleNamespace(sandbox=types.SimpleNamespace(additional_networks=["goodnet", "badnet"], workspace_mount_path_in_sandbox="/work"))
    inst.docker_client = docker_client
    inst.set_runtime_status = set_runtime_status
    inst.log = log
    inst._runtime_initialized = False
    # ensure vscode-related internal attrs exist so property accesses do not raise
    inst._vscode_enabled = False
    inst._vscode_token = None
    inst._vscode_port = 0

    # Execute connect
    await inst.connect()

    # Postconditions / assertions
    assert called_mb["called"] is True, "maybe_build_runtime_container_image should be called"
    assert setup_called == [True], "setup_initial_env should have been called once"
    # READY should be set in statuses as attach_to_existing is False
    assert RuntimeStatus.READY in statuses
    assert inst._runtime_initialized is True
    # LogStreamer (our Dummy) should have been created with the container that init_container set
    assert len(created_logstreamers) == 1
    assert created_logstreamers[0][0] is inst.container
    # goodnet should have connected our container
    assert network_connected and network_connected[0][0] == "connected"
    assert network_connected[0][1] is inst.container
    # There should be error logs about failing to connect badnet
    assert any("Failed to connect instance" in msg or "network lookup failed" in msg for _, msg in logs)
    # There should be an info log saying container started
    assert any("Container started" in msg for _, msg in logs)
    # And a debug log with plugin names
    assert any(level == "debug" and "p1" in msg and "p2" in msg for level, msg in logs)
