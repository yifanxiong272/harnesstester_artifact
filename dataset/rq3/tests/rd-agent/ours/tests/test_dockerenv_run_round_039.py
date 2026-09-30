import os
from types import SimpleNamespace
import pytest
from pathlib import Path

import rdagent.utils.env as env_mod


class FakeContainer:
    def __init__(self, logs_bytes, id_="cont-id-123", name="cont-name"):
        self._logs = list(logs_bytes)
        self.id = id_
        self.name = name

    def logs(self, stream=False):
        # Return an iterator of bytes like docker SDK
        for b in self._logs:
            yield b

    def wait(self):
        return {"StatusCode": 0}


class FakeClient:
    def __init__(self, container):
        self._container = container
        self.last_run_kwargs = None
        # docker SDK accessibility: client.containers.run
        self.containers = self

    def run(self, **kwargs):
        # record what was requested
        self.last_run_kwargs = kwargs
        return self._container


@pytest.fixture(autouse=True)
def no_real_docker(monkeypatch):
    """Patch docker calls and other side-effectful helpers in the target module.

    This prevents any real docker, filesystem, or external interactions and
    captures calls for assertions.
    """

    # Patch GPU kwargs method to avoid client inspection
    monkeypatch.setattr(env_mod.DockerEnv, "_gpu_kwargs", lambda self, client: {})

    # Patch normalize_volumes to be identity (returns same mapping)
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda vols, working_dir: vols)

    # Patch T(...) to return an object with r() -> a deterministic string
    class _T:
        def __init__(self, _):
            pass

        def r(self):
            return "/bind_cache_from_T"

    monkeypatch.setattr(env_mod, "T", _T)

    # Prevent actually creating directories on disk during tests
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=True, exist_ok=True: None)

    # Capture cleanup calls
    cleanup_calls = []

    def _cleanup(c):
        cleanup_calls.append(c)

    monkeypatch.setattr(env_mod, "cleanup_container", _cleanup)

    # Expose the captured cleanup_calls to tests via module attribute
    env_mod._test_cleanup_calls = cleanup_calls

    yield


def _make_conf(extra_volumes=None, extra_volume_mode="rw"):
    # Minimal conf-like object with attributes used by DockerEnv._run
    return SimpleNamespace(
        mount_path="/work",
        extra_volumes=extra_volumes,
        extra_volume_mode=extra_volume_mode,
        image="example/image:latest",
        network="bridge",
        shm_size="64m",
        mem_limit="512m",
        cpu_count=2,
    )


def test_run_success_with_extra_volumes_sample_round_039(monkeypatch):
    """Success path where extra_volumes contains '/sample/' -> uses /tmp/sample cache path.

    This hits env-is-None initialization, extra_volumes loop, running_extra_volume merging,
    logs iteration, container.wait(), and finally cleanup_container called with the container.
    """
    # Arrange: fake container yields two log lines as bytes
    fake_container = FakeContainer([b"first line\n", b"second line\n"])
    fake_client = FakeClient(fake_container)

    # Patch docker.from_env inside the target module to return our fake client
    monkeypatch.setattr(env_mod.docker, "from_env", lambda: fake_client)

    # Ensure docker.errors types exist and are real classes so exception tests can patch them
    # (if not present in the imported docker module, create placeholders)
    if not hasattr(env_mod.docker, "errors"):
        class _Errs: pass
        env_mod.docker.errors = _Errs()

    # Build conf with an extra_volume key including '/sample/' to force sample cache path
    conf = _make_conf(extra_volumes={"/some/sample/path": "/dest/path"}, extra_volume_mode="ro")
    docker_env = env_mod.DockerEnv(conf)

    # Act
    out, status = docker_env._run(entry="echo hi", local_path=".", env=None, running_extra_volume={"/rp": "/rbind"})

    # Assert: output contains decoded logs and status is propagated
    assert "first line" in out
    assert "second line" in out
    assert status == 0

    # The fake client's recorded kwargs should include the environment variables set by the function
    env_passed = fake_client.last_run_kwargs.get("environment")
    assert env_passed is not None
    # Confirm the function added the standard env keys
    assert env_passed.get("PYTHONWARNINGS") == "ignore"
    assert env_passed.get("TF_CPP_MIN_LOG_LEVEL") == "2"
    assert env_passed.get("PYTHONUNBUFFERED") == "1"

    # Verify volumes include the resolved absolute local path and the extra volume and cache binding
    vols = fake_client.last_run_kwargs.get("volumes")
    assert any("/rp" in k or "/some" in k or "/tmp/sample" in k for k in vols.keys())

    # cleanup_container should have been called with the actual container instance
    assert env_mod._test_cleanup_calls, "cleanup_container was not called"
    # Last call should be the container object returned by run
    assert env_mod._test_cleanup_calls[-1] is fake_container


def test_run_success_with_extra_volumes_full_round_039(monkeypatch):
    """Success path where extra_volumes does NOT contain '/sample/' -> uses /tmp/full cache path.

    Covers alternate branch for cache path selection and ensures T(...).r() is used for binding.
    """
    fake_container = FakeContainer([b"only line\n"])
    fake_client = FakeClient(fake_container)
    monkeypatch.setattr(env_mod.docker, "from_env", lambda: fake_client)

    conf = _make_conf(extra_volumes={"/another/path": "/dest"}, extra_volume_mode="rw")
    docker_env = env_mod.DockerEnv(conf)

    out, status = docker_env._run(entry=None, local_path="/tmp/some", env={"A": "B"}, running_extra_volume={})

    assert "only line" in out
    assert status == 0

    # Confirm volumes contain the /tmp/full cache path
    vols = fake_client.last_run_kwargs.get("volumes")
    assert any(k.startswith("/tmp/full") or "/tmp/full" in k for k in vols.keys())

    # cleanup_container call recorded
    assert env_mod._test_cleanup_calls[-1] is fake_container


def test_run_raises_container_error_round_039(monkeypatch):
    """Simulate docker.errors.ContainerError being raised by run and ensure it's wrapped into RuntimeError.

    Also ensure cleanup_container is invoked with None when the container was never created.
    """

    # Create a fake exception type and make docker.errors.ContainerError point to it
    class MyContainerError(Exception):
        pass

    # Ensure docker.errors exists and patch the exception class used by the module
    if not hasattr(env_mod.docker, "errors"):
        class _Errs: pass
        env_mod.docker.errors = _Errs()
    monkeypatch.setattr(env_mod.docker.errors, "ContainerError", MyContainerError, raising=False)

    # Make from_env return a client whose run raises the ContainerError
    class RaisingClient:
        containers = None

        def __init__(self):
            self.containers = self

        def run(self, **kwargs):
            raise MyContainerError("container failed: oom")

    monkeypatch.setattr(env_mod.docker, "from_env", lambda: RaisingClient())

    # Use minimal conf
    conf = _make_conf(extra_volumes=None)
    docker_env = env_mod.DockerEnv(conf)

    # Act & Assert: wrapper RuntimeError with the original message included
    with pytest.raises(RuntimeError) as ei:
        docker_env._run(entry="cmd", local_path=None, env=None, running_extra_volume={})
    assert "container failed: oom" in str(ei.value)

    # cleanup called with None (no container created)
    assert env_mod._test_cleanup_calls[-1] is None


def test_run_raises_image_not_found_round_039(monkeypatch):
    """Simulate docker.errors.ImageNotFound -> RuntimeError with specific message.
    """
    class MyImageNotFound(Exception):
        pass

    if not hasattr(env_mod.docker, "errors"):
        class _Errs: pass
        env_mod.docker.errors = _Errs()
    monkeypatch.setattr(env_mod.docker.errors, "ImageNotFound", MyImageNotFound, raising=False)

    class RaisingClient:
        containers = None

        def __init__(self):
            self.containers = self

        def run(self, **kwargs):
            raise MyImageNotFound()

    monkeypatch.setattr(env_mod.docker, "from_env", lambda: RaisingClient())

    conf = _make_conf()
    docker_env = env_mod.DockerEnv(conf)

    with pytest.raises(RuntimeError) as ei:
        docker_env._run(entry="cmd", local_path=None, env=None, running_extra_volume={})
    assert "Docker image not found." in str(ei.value)

    # cleanup called
    assert env_mod._test_cleanup_calls[-1] is None


def test_run_raises_api_error_round_039(monkeypatch):
    """Simulate docker.errors.APIError -> RuntimeError wrapping the original error.
    """
    class MyAPIError(Exception):
        pass

    if not hasattr(env_mod.docker, "errors"):
        class _Errs: pass
        env_mod.docker.errors = _Errs()
    monkeypatch.setattr(env_mod.docker.errors, "APIError", MyAPIError, raising=False)

    class RaisingClient:
        containers = None

        def __init__(self):
            self.containers = self

        def run(self, **kwargs):
            raise MyAPIError("api down")

    monkeypatch.setattr(env_mod.docker, "from_env", lambda: RaisingClient())

    conf = _make_conf()
    docker_env = env_mod.DockerEnv(conf)

    with pytest.raises(RuntimeError) as ei:
        docker_env._run(entry="cmd", local_path=None, env=None, running_extra_volume={})
    assert "api down" in str(ei.value)

    # cleanup called
    assert env_mod._test_cleanup_calls[-1] is None
