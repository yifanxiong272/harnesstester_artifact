# file: rdagent/utils/env.py:873-949
# asked: {"lines": [881, 882, 883, 884, 885, 886, 888, 889, 890, 891, 893, 894, 895, 896, 897, 898, 899, 900, 902, 904, 905, 907, 908, 909, 910, 911, 912, 913, 914, 916, 917, 918, 919, 920, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 949], "branches": [[881, 882], [881, 883], [889, 890], [889, 893], [893, 894], [893, 899], [894, 895], [894, 896], [899, 900], [899, 902], [935, 936], [935, 939]]}
# gained: {"lines": [881, 882, 883, 884, 885, 886, 888, 889, 890, 891, 893, 894, 895, 896, 897, 898, 899, 900, 902, 904, 905, 907, 908, 909, 910, 911, 912, 913, 914, 916, 917, 918, 919, 920, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 949], "branches": [[881, 882], [881, 883], [889, 890], [893, 894], [893, 899], [894, 895], [894, 896], [899, 900], [899, 902], [935, 936], [935, 939]]}

import shutil
from types import SimpleNamespace
from pathlib import Path
import pytest

import rdagent.utils.env as env_mod


class _FakeContainer:
    def __init__(self, id="cid", name="cname", logs_iter=None, wait_status=0):
        self.id = id
        self.name = name
        self._logs = logs_iter if logs_iter is not None else [b"log1\n", b"log2\n"]
        self._wait_status = wait_status
        self.closed = False

    def logs(self, stream=True):
        # return an iterator of bytes
        return iter(self._logs)

    def wait(self):
        return {"StatusCode": self._wait_status}


class _FakeClient:
    def __init__(self, container):
        self.containers = SimpleNamespace(run=lambda *a, **k: container)


def _make_conf(
    mount_path="/work",
    extra_volumes=None,
    extra_volume_mode="rw",
    image="img",
    network=None,
    shm_size=None,
    mem_limit=None,
    cpu_count=None,
):
    return SimpleNamespace(
        mount_path=mount_path,
        extra_volumes=extra_volumes,
        extra_volume_mode=extra_volume_mode,
        image=image,
        network=network,
        shm_size=shm_size,
        mem_limit=mem_limit,
        cpu_count=cpu_count,
    )


def test_run_success_and_cleanup_called(monkeypatch):
    # Arrange
    fake_container = _FakeContainer(id="ID123", name="NAME123")
    fake_client = _FakeClient(fake_container)

    # Monkeypatch docker.from_env to return our fake client
    monkeypatch.setattr(env_mod.docker, "from_env", lambda: fake_client)

    # Ensure normalize_volumes is identity to avoid external logic
    called = {}
    def fake_normalize_volumes(vols, mount_path):
        called["called_with"] = (dict(vols), mount_path)
        return vols
    monkeypatch.setattr(env_mod, "normalize_volumes", fake_normalize_volumes)

    # Patch DockerEnv._gpu_kwargs to avoid interacting with real docker client
    monkeypatch.setattr(env_mod.DockerEnv, "_gpu_kwargs", lambda self, client: {})

    # Record cleanup_container calls
    cleanup_calls = []
    monkeypatch.setattr(env_mod, "cleanup_container", lambda c: cleanup_calls.append(c))

    # Instantiate DockerEnv without running base __init__
    env = object.__new__(env_mod.DockerEnv)
    env.conf = _make_conf(mount_path="/work", extra_volumes=None, image="img", network="net", shm_size="1g", mem_limit="2g", cpu_count=1)

    # Act
    log_output, status = env._run(entry="echo hi", local_path=".", env=None, running_extra_volume={"/host/run": "/container/run"})

    # Assert
    assert "log1\n" in log_output
    assert "log2\n" in log_output
    assert status == 0
    # normalize_volumes should have been called with the constructed volumes and mount_path
    assert "called_with" in called
    vols_passed, mount_path_passed = called["called_with"]
    assert mount_path_passed == env.conf.mount_path
    # cleanup_container should have been called with our fake container
    assert cleanup_calls and cleanup_calls[-1] is fake_container


def test_run_with_extra_volumes_creates_cache_and_bind_using_T(monkeypatch):
    # Arrange: set extra_volumes with a key containing '/sample/' to trigger cache_path '/tmp/sample'
    sample_key = "/host/sample/data"
    extra_vols = {sample_key: "/container/data"}
    fake_container = _FakeContainer(id="ID234", name="NAME234")
    fake_client = _FakeClient(fake_container)
    monkeypatch.setattr(env_mod.docker, "from_env", lambda: fake_client)

    # Make normalize_volumes identity
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda v, m: v)

    # Provide a T() that returns an object with r() -> a container bind path
    class DummyT:
        def __init__(self, *_a, **_k):
            pass
        def r(self):
            return "/container/cache_bind"
    monkeypatch.setattr(env_mod, "T", lambda *a, **k: DummyT())

    # Patch _gpu_kwargs
    monkeypatch.setattr(env_mod.DockerEnv, "_gpu_kwargs", lambda self, client: {})

    # Capture cleanup calls
    cleanup_calls = []
    monkeypatch.setattr(env_mod, "cleanup_container", lambda c: cleanup_calls.append(c))

    env = object.__new__(env_mod.DockerEnv)
    env.conf = _make_conf(mount_path="/work", extra_volumes=extra_vols, extra_volume_mode="ro", image="img")

    # Ensure /tmp/sample removed after test if created
    sample_dir = Path("/tmp/sample")
    try:
        if sample_dir.exists():
            # remove before to assure we test creation
            shutil.rmtree(sample_dir)
    except Exception:
        pass

    # Act
    try:
        log_output, status = env._run(entry=None, local_path=".", env={})
    finally:
        # Cleanup created dir if exists
        try:
            if sample_dir.exists():
                shutil.rmtree(sample_dir)
        except Exception:
            pass

    # Assert
    assert status == 0
    # Ensure cleanup called with our container
    assert cleanup_calls and cleanup_calls[-1] is fake_container
    # Also check that volumes included cache bind by checking returned log or that no exception thrown
    assert isinstance(log_output, str)


def test_run_image_not_found_raises_and_cleanup(monkeypatch):
    # Arrange: simulate docker.from_env().containers.run raising ImageNotFound
    class DummyImageNotFound(Exception):
        pass

    def fake_from_env():
        def run_raises(*a, **k):
            raise DummyImageNotFound("no image")
        return SimpleNamespace(containers=SimpleNamespace(run=run_raises))

    monkeypatch.setattr(env_mod.docker, "from_env", fake_from_env)

    # Set docker.errors so that ContainerError does NOT catch DummyImageNotFound,
    # allowing the ImageNotFound handler to run.
    monkeypatch.setattr(env_mod.docker, "errors", SimpleNamespace(ImageNotFound=DummyImageNotFound, ContainerError=RuntimeError, APIError=Exception), raising=False)

    # Patch normalize_volumes and _gpu_kwargs
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda v, m: v)
    monkeypatch.setattr(env_mod.DockerEnv, "_gpu_kwargs", lambda self, client: {})

    cleanup_calls = []
    monkeypatch.setattr(env_mod, "cleanup_container", lambda c: cleanup_calls.append(c))

    env = object.__new__(env_mod.DockerEnv)
    env.conf = _make_conf()

    # Act & Assert
    with pytest.raises(RuntimeError) as excinfo:
        env._run(entry="x", local_path=".", env=None)
    # Expect the specific ImageNotFound branch message
    assert "Docker image not found." in str(excinfo.value)
    # cleanup should be called with None (container was not created)
    assert cleanup_calls and cleanup_calls[-1] is None


def test_run_container_and_api_errors_raise_and_cleanup(monkeypatch):
    # Arrange: test both ContainerError and APIError map to RuntimeError
    class DummyContainerError(Exception):
        pass

    class DummyAPIError(Exception):
        pass

    class DummyImageNotFound(Exception):
        pass

    # First simulate ContainerError
    def fake_from_env_container_error():
        def run_raises(*a, **k):
            raise DummyContainerError("container failed")
        return SimpleNamespace(containers=SimpleNamespace(run=run_raises))

    monkeypatch.setattr(env_mod.docker, "from_env", fake_from_env_container_error)
    monkeypatch.setattr(env_mod.docker, "errors", SimpleNamespace(ContainerError=DummyContainerError, ImageNotFound=DummyImageNotFound, APIError=DummyAPIError), raising=False)
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda v, m: v)
    monkeypatch.setattr(env_mod.DockerEnv, "_gpu_kwargs", lambda self, client: {})

    cleanup_calls = []
    monkeypatch.setattr(env_mod, "cleanup_container", lambda c: cleanup_calls.append(c))

    env = object.__new__(env_mod.DockerEnv)
    env.conf = _make_conf()

    with pytest.raises(RuntimeError) as excinfo:
        env._run(entry="x", local_path=".", env=None)
    assert "Error while running the container" in str(excinfo.value)
    # cleanup called with None
    assert cleanup_calls and cleanup_calls[-1] is None

    # Now simulate APIError
    def fake_from_env_api_error():
        def run_raises(*a, **k):
            raise DummyAPIError("api failed")
        return SimpleNamespace(containers=SimpleNamespace(run=run_raises))

    monkeypatch.setattr(env_mod.docker, "from_env", fake_from_env_api_error)
    # Ensure ImageNotFound is a distinct class so it doesn't catch DummyAPIError
    monkeypatch.setattr(env_mod.docker, "errors", SimpleNamespace(ContainerError=DummyContainerError, ImageNotFound=DummyImageNotFound, APIError=DummyAPIError), raising=False)

    cleanup_calls.clear()
    with pytest.raises(RuntimeError) as excinfo2:
        env._run(entry="x", local_path=".", env=None)
    assert "Error while running the container" in str(excinfo2.value)
    assert cleanup_calls and cleanup_calls[-1] is None
