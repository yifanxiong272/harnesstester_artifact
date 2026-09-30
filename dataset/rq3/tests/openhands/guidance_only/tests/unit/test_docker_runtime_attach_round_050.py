import types
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.docker.docker_runtime import DockerRuntime


class FakeContainer:
    def __init__(self, status, attrs):
        self.status = status
        self.attrs = attrs
        self.started = False

    def start(self):
        # mutate internal state so tests can assert start was invoked
        self.started = True


class FakeContainersAccessor:
    def __init__(self, container):
        self._container = container

    def get(self, name):
        assert name == "test-container"
        return self._container


class FakeDockerClient:
    def __init__(self, container):
        self.containers = FakeContainersAccessor(container)


def make_runtime_instance():
    # create an instance without running __init__ and populate only needed attributes
    rt = DockerRuntime.__new__(DockerRuntime)
    rt.container_name = "test-container"
    # log collector
    rt._logged = []

    def log(level, msg):
        rt._logged.append((level, msg))

    rt.log = log
    # config with sandbox.local_runtime_url
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(local_runtime_url="http://sandbox"))
    # default ports --- tests will set or rely on these as needed
    rt._host_port = None
    rt._container_port = None
    rt._vscode_port = None
    rt._app_ports = []
    return rt


def test_attach_to_container_start_and_ports_round_050():
    """
    - container.status == 'exited' should call start()
    - env contains 'port=' and 'VSCODE_PORT=' should set _host_port/_container_port and _vscode_port
    - ExposedPorts should parse /tcp keys and exclude host and vscode ports, appending others
    - api_url should be constructed from config.sandbox.local_runtime_url and _container_port
    - log should be invoked with debug message containing container_name and port
    """
    # prepare fake container with exited status and attrs matching expected shape
    config = {
        "Config": {
            "Env": ["SOME=val", "port=1234", "VSCODE_PORT=5678"],
            "ExposedPorts": {"1234/tcp": {}, "8000/tcp": {}, "5678/tcp": {}},
        }
    }
    container = FakeContainer(status="exited", attrs=config)
    fake_client = FakeDockerClient(container=container)

    rt = make_runtime_instance()
    rt.docker_client = fake_client

    # Call method under test
    rt._attach_to_container()

    # Assertions
    assert container.started is True, "container.start() should be called when status is 'exited'"
    assert rt._host_port == 1234, "_host_port must be set from env 'port='"
    assert rt._container_port == 1234, "_container_port must be set equal to _host_port"
    assert rt._vscode_port == 5678, "_vscode_port must be set from 'VSCODE_PORT='"
    # Exposed ports: 1234 and 5678 excluded, 8000 included
    assert rt._app_ports == [8000], "only non-host and non-vscode exposed ports must be appended"
    assert rt.api_url == "http://sandbox:1234"
    # log should have recorded the debug message
    assert any(
        entry[0] == "debug" and "test-container" in entry[1] and "1234" in entry[1]
        for entry in rt._logged
    )


def test_attach_to_container_no_start_and_no_exposed_round_050():
    """
    - container.status != 'exited' should NOT call start()
    - when Env does not contain port entries, existing _host_port/_container_port/_vscode_port are preserved
    - when ExposedPorts is None, _app_ports remains empty
    - api_url uses current _container_port
    """
    # prepare fake container with running status and no special envs
    config = {
        "Config": {
            "Env": ["OTHER=1", "ANOTHER=2"],
            # ExposedPorts missing or None
        }
    }
    container = FakeContainer(status="running", attrs=config)
    fake_client = FakeDockerClient(container=container)

    rt = make_runtime_instance()
    rt.docker_client = fake_client
    # set defaults so _attach_to_container will not fail when env vars are absent
    rt._host_port = 2222
    rt._container_port = 2222
    rt._vscode_port = 3333
    rt._app_ports = [9999]  # start non-empty to verify method resets only when needed

    # Call method under test
    rt._attach_to_container()

    # Assertions
    assert container.started is False, "container.start() should NOT be called when status != 'exited'"
    # Since no env port settings provided, attributes should remain as set prior
    assert rt._host_port == 2222
    assert rt._container_port == 2222
    assert rt._vscode_port == 3333
    # ExposedPorts missing => no changes to _app_ports caused by parsing; should become [] per implementation
    # Implementation sets self._app_ports = [] at line 570 unconditionally, so expect empty list
    assert rt._app_ports == []
    assert rt.api_url == "http://sandbox:2222"
    assert any(entry[0] == "debug" and "test-container" in entry[1] for entry in rt._logged)
