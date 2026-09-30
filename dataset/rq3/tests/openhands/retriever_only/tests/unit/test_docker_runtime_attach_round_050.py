import types

from openhands.runtime.impl.docker import docker_runtime


class _FakeContainer:
    def __init__(self, status, env_list, exposed_ports=None):
        self.status = status
        self._started = False
        # attributes look like docker container.attrs
        self.attrs = {"Config": {"Env": env_list}}
        if exposed_ports is not None:
            # docker exposes ports as a dict with keys like '8000/tcp'
            self.attrs["Config"]["ExposedPorts"] = {f"{p}/tcp": {} for p in exposed_ports}

    def start(self):
        # mark that start was called
        self._started = True


class _FakeContainersCollection:
    def __init__(self, container):
        self._container = container

    def get(self, name):
        # ignore name, return the prepared container
        return self._container


class _FakeDockerClient:
    def __init__(self, container):
        self.containers = _FakeContainersCollection(container)


class _FakeSandbox:
    def __init__(self, local_runtime_url):
        self.local_runtime_url = local_runtime_url


class _FakeConfig:
    def __init__(self, local_runtime_url="http://localhost"):
        self.sandbox = _FakeSandbox(local_runtime_url)


class _FakeSelf:
    def __init__(self, docker_client, container_name, config=None):
        self.docker_client = docker_client
        self.container_name = container_name
        self.config = config or _FakeConfig()
        # collect log calls for assertions
        self.logged = []

    def log(self, level, message):
        # store simple tuple so tests can assert calls
        self.logged.append((level, message))


def _call_attach(fake_self):
    # call the function object defined on the real class as an unbound function
    # This executes the real implementation under test with our fake 'self'
    func = docker_runtime.DockerRuntime._attach_to_container
    # call as unbound method
    return func(fake_self)


def test_attach_with_exited_container_and_exposed_ports_round_050():
    # prepare a container that is 'exited' so .start() should be invoked
    env = [
        "port=12345",
        "VSCODE_PORT=23456",
        "OTHER=1",
    ]
    # Expose three ports: one equal to host (12345), one equal to vscode (23456), and one extra 8000
    container = _FakeContainer(status="exited", env_list=env, exposed_ports=[12345, 23456, 8000])
    docker_client = _FakeDockerClient(container)

    fake = _FakeSelf(docker_client=docker_client, container_name="my-container", config=_FakeConfig("http://runtime"))

    # run the real method
    _call_attach(fake)

    # container.start() should have been called because status was 'exited'
    assert getattr(container, "_started", False) is True

    # host and container port should be set from env port=
    assert getattr(fake, "_host_port") == 12345
    assert getattr(fake, "_container_port") == 12345

    # vscode port should be set from env
    assert getattr(fake, "_vscode_port") == 23456

    # _app_ports should include only the extra exposed port (8000), not the host/vscode ones
    assert sorted(getattr(fake, "_app_ports")) == [8000]

    # api_url should be composed from sandbox local_runtime_url and container port
    assert fake.api_url == "http://runtime:12345"

    # a debug log call should have been recorded with container name and ports
    assert any(
        entry[0] == "debug" and "attached to container: my-container" in entry[1]
        for entry in fake.logged
    )


def test_attach_with_running_container_and_no_exposed_ports_round_050():
    # prepare a container that is already running so .start() should NOT be invoked
    env = [
        # deliberately omit port= and VSCODE_PORT= to simulate missing env vars
        "SOME=VALUE",
    ]
    container = _FakeContainer(status="running", env_list=env, exposed_ports=None)
    docker_client = _FakeDockerClient(container)

    fake = _FakeSelf(docker_client=docker_client, container_name="other", config=_FakeConfig("http://example"))
    # Prepopulate ports on fake so code can still compare them later if needed
    fake._host_port = 11111
    fake._container_port = 11111
    fake._vscode_port = 22222

    # run the real method - should not call container.start()
    _call_attach(fake)

    # start should NOT have been called for a running container
    assert getattr(container, "_started", False) is False

    # Because container.attrs had no ExposedPorts, _app_ports should be an empty list
    assert getattr(fake, "_app_ports") == []

    # api_url should reflect the prepopulated container port
    assert fake.api_url == "http://example:11111"

    # ensure a debug log entry was created
    assert any(entry[0] == "debug" for entry in fake.logged)
