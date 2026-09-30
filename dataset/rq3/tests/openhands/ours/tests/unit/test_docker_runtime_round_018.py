import types
import pytest
import asyncio

import builtins

import openhands.runtime.impl.docker.docker_runtime as docker_runtime_module

# All test functions/classes MUST end with _round_018

@pytest.mark.asyncio
async def test_connect_attach_to_existing_not_found_raises_and_logs_round_018(monkeypatch):
    """
    Scenario: _attach_to_container raises docker.errors.NotFound and attach_to_existing is True.
    Expectation: AgentRuntimeDisconnectedError is raised and a warning log mentioning the container is produced.
    """
    # Prepare a fake NotFound exception class (ensure deterministic behavior regardless of real docker package)
    class FakeNotFound(Exception):
        pass

    # Patch the module's docker.errors.NotFound so the except clause matches our raised exception
    # Ensure docker attribute exists on the module
    if not hasattr(docker_runtime_module, "docker"):
        docker_runtime_module.docker = types.SimpleNamespace()
        docker_runtime_module.docker.errors = types.SimpleNamespace()
    docker_runtime_module.docker.errors.NotFound = FakeNotFound

    # Fake call_sync_from_async to synchronously call the supplied function (wrapped as an async function)
    async def fake_call_sync_from_async(func, *args, **kwargs):
        # If it's a coroutine function, await it; otherwise call directly
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    monkeypatch.setattr(docker_runtime_module, "call_sync_from_async", fake_call_sync_from_async)

    # Create a minimal 'self' with attributes used by connect
    logs = []

    def record_log(level, message):
        logs.append((level, message))

    # _attach_to_container will raise the NotFound we patched above
    def raise_not_found():
        raise FakeNotFound("container missing")

    self = types.SimpleNamespace()
    self.set_runtime_status_calls = []

    def set_runtime_status(status):
        self.set_runtime_status_calls.append(status)

    self.set_runtime_status = set_runtime_status
    self._attach_to_container = raise_not_found
    self.attach_to_existing = True
    self.log = record_log
    self.container_name = "container_xyz"

    # Ensure required attributes referenced later exist (no-op)
    self.maybe_build_runtime_container_image = lambda: None
    self.runtime_container_image = "img:latest"
    self.init_container = lambda: None
    self.vscode_url = "http://vscode"
    self.api_url = "http://api"
    self.wait_until_alive = lambda: None
    self.setup_initial_env = lambda: None
    self.plugins = []
    self._runtime_initialized = False
    self.config = types.SimpleNamespace()
    self.config.sandbox = types.SimpleNamespace(additional_networks=[])
    self.docker_client = types.SimpleNamespace()

    # Run and assert
    with pytest.raises(docker_runtime_module.AgentRuntimeDisconnectedError):
        await docker_runtime_module.DockerRuntime.connect(self)

    # Verify that a warning mentioning the container name was logged
    assert any(level == "warning" and self.container_name in message for level, message in logs), (
        "Expected a warning log containing the container name when attach_to_existing=True and container not found"
    )


@pytest.mark.asyncio
async def test_connect_builds_initializes_and_networks_round_018(monkeypatch):
    """
    Scenario: _attach_to_container raises NotFound and attach_to_existing is False.
    - Should call maybe_build_runtime_container_image
    - Should call init_container, wait_until_alive, setup_initial_env
    - When DEBUG_RUNTIME is True and container present -> LogStreamer constructed
    - Should attempt to connect to additional networks; handle success and a failing network (exception)
    """
    # Provide deterministic NotFound class and patch into module
    class FakeNotFound(Exception):
        pass

    if not hasattr(docker_runtime_module, "docker"):
        docker_runtime_module.docker = types.SimpleNamespace()
        docker_runtime_module.docker.errors = types.SimpleNamespace()
    docker_runtime_module.docker.errors.NotFound = FakeNotFound

    # Make call_sync_from_async run synchronous callables in an awaitable wrapper
    async def fake_call_sync_from_async(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    monkeypatch.setattr(docker_runtime_module, "call_sync_from_async", fake_call_sync_from_async)

    # Force DEBUG_RUNTIME True in the module under test to exercise LogStreamer branch
    monkeypatch.setattr(docker_runtime_module, "DEBUG_RUNTIME", True)

    # Replace LogStreamer with a fake that records initialization parameters
    created_logstreamers = []

    class FakeLogStreamer:
        def __init__(self, container, log_callable):
            created_logstreamers.append((container, log_callable))

    monkeypatch.setattr(docker_runtime_module, "LogStreamer", FakeLogStreamer)

    # Prepare logging capture
    logs = []

    def record_log(level, message):
        logs.append((level, message))

    # Track calls to lifecycle methods
    called = {
        "maybe_build": 0,
        "init_container": 0,
        "wait_until_alive": 0,
        "setup_initial_env": 0,
    }

    def maybe_build_runtime_container_image():
        called["maybe_build"] += 1

    def init_container():
        called["init_container"] += 1

    def wait_until_alive():
        called["wait_until_alive"] += 1

    def setup_initial_env():
        called["setup_initial_env"] += 1

    # _attach_to_container raises NotFound to enter the image build / init path
    def raise_not_found():
        raise FakeNotFound("not found for init path")

    # Construct a fake docker_client.networks.get behavior: one network connects fine, another raises
    class FakeNetworkOk:
        def __init__(self):
            self.connected = False

        def connect(self, container):
            self.connected = True

    class FakeNetworks:
        def __init__(self, fail_on=None):
            self.fail_on = fail_on

        def get(self, name):
            if name == "net_bad":
                raise Exception("network lookup failed")
            return FakeNetworkOk()

    fake_networks = FakeNetworks()

    docker_client = types.SimpleNamespace(networks=fake_networks)

    # Build the self object
    self = types.SimpleNamespace()
    statuses = []

    def set_runtime_status(status):
        statuses.append(status)

    self.set_runtime_status = set_runtime_status
    self._attach_to_container = raise_not_found
    self.attach_to_existing = False
    self.log = record_log
    self.maybe_build_runtime_container_image = maybe_build_runtime_container_image
    self.runtime_container_image = "img:init"
    self.init_container = init_container
    self.vscode_url = "http://vscode"
    self.api_url = "http://api"
    self.wait_until_alive = wait_until_alive
    self.setup_initial_env = setup_initial_env
    # Provide a present container so networks.connect(self.container) branch runs
    self.container = object()
    self.plugins = [types.SimpleNamespace(name="p1")]
    self._runtime_initialized = False
    # Provide two networks: one ok, one bad
    self.config = types.SimpleNamespace()
    self.config.sandbox = types.SimpleNamespace(additional_networks=["net_ok", "net_bad"])
    self.docker_client = docker_client
    self.container_name = "container_init"

    # Run connect
    await docker_runtime_module.DockerRuntime.connect(self)

    # Assertions for lifecycle calls
    assert called["maybe_build"] == 1, "Expected maybe_build_runtime_container_image to be called once"
    assert called["init_container"] == 1, "Expected init_container to be called once"
    assert called["wait_until_alive"] == 1, "Expected wait_until_alive to be called once"
    assert called["setup_initial_env"] == 1, "Expected setup_initial_env to be called once"

    # DEBUG_RUNTIME True and container present should create a LogStreamer instance
    assert len(created_logstreamers) == 1, "Expected a LogStreamer to be created when DEBUG_RUNTIME and container are set"
    created_container, created_log_callable = created_logstreamers[0]
    assert created_container is self.container
    assert created_log_callable is self.log

    # After successful init, runtime should be marked initialized and statuses should include READY
    assert self._runtime_initialized is True, "_runtime_initialized should be True after successful connect"
    # Expect that RUNNING/STARTING and READY statuses were toggled (STARTING appears at least once and READY should appear)
    assert any(s == docker_runtime_module.RuntimeStatus.READY for s in statuses), "Expected RuntimeStatus.READY to be set"
    assert any(s == docker_runtime_module.RuntimeStatus.STARTING_RUNTIME for s in statuses), "Expected STARTING_RUNTIME to be set at least once"

    # Network assertions: first network should have been connected (we can't get instance directly, but log entries should capture failures)
    # The second network should have triggered error logs
    assert any(level == "error" and "Failed to connect instance" in msg for level, msg in logs), (
        "Expected an error log when network connection failed"
    )
