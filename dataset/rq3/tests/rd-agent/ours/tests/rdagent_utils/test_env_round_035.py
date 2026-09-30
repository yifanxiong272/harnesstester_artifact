import json
from types import SimpleNamespace
import pytest

import rdagent.utils.env as env_module


class DummyProgress:
    def __init__(self, *args, **kwargs):
        self._tasks = {}
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def add_task(self, description, **kwargs):
        tid = f"task-{len(self._tasks)+1}"
        self._tasks[tid] = {"description": description, "fields": {}}
        return tid
    def update(self, task, **kwargs):
        # record updates in a minimal predictable way
        if task in self._tasks:
            self._tasks[task].update(kwargs)


class FakePath:
    def __init__(self, path_str="/fake/path", exists_val=True):
        self._s = path_str
        self._exists = exists_val
    def exists(self):
        return self._exists
    def __str__(self):
        return self._s


def make_conf(build_from_dockerfile=False, path_exists=True, image="my:img", network=None):
    return SimpleNamespace(
        build_from_dockerfile=build_from_dockerfile,
        dockerfile_folder_path=FakePath("/fake/dockerfile", exists_val=path_exists),
        image=image,
        network=network,
    )


def test_build_from_dockerfile_resp_stream_str_round_035(monkeypatch):
    """
    When build_from_dockerfile is True and client.api.build returns a string,
    the code should call build and log the returned string.
    """
    # Patch Progress to avoid dependency on rich terminal behaviour
    monkeypatch.setattr(env_module, "Progress", DummyProgress)

    # Capture logger.info calls
    logs = []
    class FakeLogger:
        def info(self, msg):
            logs.append(msg)
    monkeypatch.setattr(env_module, "logger", FakeLogger())

    # Prepare fake client: api.build returns a string; images.get succeeds
    class FakeAPI:
        def __init__(self):
            self.build_calls = []
        def build(self, path, tag, network_mode):
            self.build_calls.append((path, tag, network_mode))
            return "BUILD-LOG-STRING"
    fake_api = FakeAPI()
    fake_client = SimpleNamespace(api=fake_api, images=SimpleNamespace(get=lambda img: True))

    # Ensure docker.from_env returns our fake client
    monkeypatch.setattr(env_module.docker, "from_env", lambda: fake_client)

    # Create an object to serve as self for the unbound method
    self_obj = SimpleNamespace(conf=make_conf(build_from_dockerfile=True, path_exists=True, image="image:tag", network="bridge"))

    # Call prepare
    env_module.DockerEnv.prepare(self_obj)

    # Assertions: build called with expected args and logger recorded build-info and build log
    assert fake_api.build_calls == [(str(self_obj.conf.dockerfile_folder_path), self_obj.conf.image, self_obj.conf.network)]
    # First logger.info should mention building from dockerfile path
    assert any(str(self_obj.conf.dockerfile_folder_path) in str(m) for m in logs), "dockerfile build info not logged"
    # The resp_stream string should also be logged
    assert any("BUILD-LOG-STRING" in str(m) for m in logs), "build response string not logged"


def test_build_from_dockerfile_resp_stream_iter_error_round_035(monkeypatch):
    """
    When client.api.build yields an iterable of byte-chunks containing a JSON error line,
    the code should raise the docker.errors.BuildError produced from that JSON.
    """
    monkeypatch.setattr(env_module, "Progress", DummyProgress)

    # Provide a BuildError class in docker.errors for the code to raise
    class FakeBuildError(Exception):
        pass
    # Ensure docker.errors has BuildError attribute (create if needed)
    if not hasattr(env_module.docker, "errors"):
        env_module.docker.errors = SimpleNamespace()
    monkeypatch.setattr(env_module.docker.errors, "BuildError", FakeBuildError, raising=False)

    # Fake API returning iterable of bytes that decode to an error JSON line
    class FakeAPI:
        def build(self, path, tag, network_mode):
            return [b'{"error": "boom-build"}\r\n']
    fake_client = SimpleNamespace(api=FakeAPI(), images=SimpleNamespace(get=lambda img: True))
    monkeypatch.setattr(env_module.docker, "from_env", lambda: fake_client)

    self_obj = SimpleNamespace(conf=make_conf(build_from_dockerfile=True, path_exists=True, image="image:tag", network=None))

    with pytest.raises(FakeBuildError):
        env_module.DockerEnv.prepare(self_obj)


def test_pull_image_image_not_found_api_error_round_035(monkeypatch):
    """
    When images.get raises ImageNotFound and client.api.pull yields a dict with an 'error'
    the code should raise a RuntimeError that wraps the docker.errors.APIError.
    """
    monkeypatch.setattr(env_module, "Progress", DummyProgress)

    # Ensure docker.errors has the necessary exception classes
    class FakeImageNotFound(Exception):
        pass
    class FakeAPIError(Exception):
        pass

    if not hasattr(env_module.docker, "errors"):
        env_module.docker.errors = SimpleNamespace()
    monkeypatch.setattr(env_module.docker.errors, "ImageNotFound", FakeImageNotFound, raising=False)
    monkeypatch.setattr(env_module.docker.errors, "APIError", FakeAPIError, raising=False)

    # Fake client where images.get raises ImageNotFound
    def images_get_fail(name):
        raise FakeImageNotFound("not found")

    # api.pull yields a single line that contains an 'error' key -> triggers APIError -> wrapped
    class FakeAPI:
        def pull(self, image, stream, decode):
            # Iteration yields mapping objects as the real decode=True yields
            yield {"error": "pull-fail"}
    fake_client = SimpleNamespace(api=FakeAPI(), images=SimpleNamespace(get=images_get_fail))

    monkeypatch.setattr(env_module.docker, "from_env", lambda: fake_client)

    self_obj = SimpleNamespace(conf=make_conf(build_from_dockerfile=False, path_exists=False, image="some/image:tag", network=None))

    with pytest.raises(RuntimeError) as excinfo:
        env_module.DockerEnv.prepare(self_obj)
    # The underlying error message should be surfaced inside the RuntimeError message
    assert "pull-fail" in str(excinfo.value)
