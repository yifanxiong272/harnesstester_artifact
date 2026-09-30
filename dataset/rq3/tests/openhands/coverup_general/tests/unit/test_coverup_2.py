# file: openhands/runtime/builder/docker.py:61-262
# asked: {"lines": [89, 90, 91, 92, 93, 94, 95, 96, 98, 99, 100, 103, 104, 106, 111, 112, 114, 127, 128, 129, 130, 132, 133, 134, 135, 136, 138, 139, 140, 142, 143, 144, 145, 146, 147, 148, 149, 150, 154, 155, 157, 158, 159, 160, 161, 162, 166, 167, 169, 171, 172, 175, 176, 177, 180, 183, 184, 185, 188, 189, 192, 193, 194, 195, 196, 197, 198, 200, 202, 204, 205, 206, 207, 208, 209, 212, 213, 214, 215, 216, 217, 218, 220, 221, 222, 224, 225, 226, 228, 229, 230, 232, 234, 235, 236, 238, 240, 241, 242, 243, 244, 248, 249, 250, 251, 254, 255, 256, 257, 259, 260, 262], "branches": [[98, 99], [98, 103], [103, 104], [103, 106], [106, 111], [106, 138], [127, 128], [127, 136], [154, 155], [154, 157], [158, 159], [158, 166], [166, 167], [166, 169], [193, 194], [193, 200], [194, 195], [194, 200], [196, 194], [196, 197], [202, 204], [202, 238], [214, 215], [214, 216], [216, 217], [216, 218], [240, 241], [240, 248], [249, 250], [249, 254]]}
# gained: {"lines": [89, 90, 91, 92, 93, 94, 98, 103, 106, 111, 112, 114, 127, 128, 129, 130, 132, 133, 134, 135, 138, 139, 140, 142, 143, 144, 145, 146, 147, 148, 149, 150, 154, 155, 157, 158, 159, 160, 161, 162, 166, 167, 169, 171, 172, 175, 176, 177, 180, 183, 184, 185, 188, 189, 192, 193, 194, 195, 196, 197, 198, 200, 202, 204, 205, 206, 207, 208, 209, 212, 213, 214, 215, 216, 217, 218, 220, 221, 222, 238, 240, 241, 242, 243, 244, 248, 249, 254, 255, 256, 259, 260, 262], "branches": [[98, 103], [103, 106], [106, 111], [106, 138], [127, 128], [154, 155], [154, 157], [158, 159], [158, 166], [166, 167], [166, 169], [193, 194], [193, 200], [194, 195], [194, 200], [196, 197], [202, 204], [202, 238], [214, 215], [214, 216], [216, 217], [240, 241], [249, 254]]}

import subprocess
from unittest.mock import Mock
import pytest

from openhands.core.exceptions import AgentRuntimeBuildError
from openhands.runtime.builder.docker import DockerRuntimeBuilder


class FakeStdout:
    def __init__(self, lines):
        # lines should be list of strings returned by readline until ''
        self._lines = list(lines)

    def readline(self):
        if not self._lines:
            return ''
        return self._lines.pop(0)


class FakeProcess:
    def __init__(self, lines=None, return_code=0, wait_exception=None):
        self.stdout = FakeStdout(lines or []) if lines is not None else None
        self.args = ['docker', 'buildx', 'build']
        self._return_code = return_code
        self._wait_exception = wait_exception

    def wait(self):
        if self._wait_exception:
            raise self._wait_exception
        return self._return_code


def make_docker_client(version='19.03.12', components=None, image_obj=None):
    docker_client = Mock()
    docker_client.version.return_value = {'Version': version, 'Components': components}
    images = Mock()
    images.get = Mock(return_value=image_obj)
    docker_client.images = images
    return docker_client


def test_build_success_with_platform_cache_and_extra_args(monkeypatch):
    # Arrange: docker version high enough, check_buildx True, cache usable True, and Popen returns success
    img = Mock()
    img.tag = Mock()
    docker_client = make_docker_client(version='19.03.12', components=None, image_obj=img)

    # Ensure module uses our docker client when calling docker.from_env()
    monkeypatch.setattr('openhands.runtime.builder.docker.docker.from_env', lambda: docker_client)

    builder = DockerRuntimeBuilder(docker_client)

    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder.check_buildx', staticmethod(lambda is_podman=False: True))
    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder._is_cache_usable', lambda self, d: True)

    fake_proc = FakeProcess(lines=['Step 1 completed\n', 'Step 2 completed\n', ''], return_code=0)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: fake_proc)

    # Act
    tags = ['myrepo:sha123', 'myrepo:latest']
    result = builder.build(path='.', tags=tags, platform='linux/amd64', extra_build_args=['--no-cache'], use_local_cache=True)

    # Assert
    assert result == tags[0]
    docker_client.images.get.assert_called_with(tags[0])
    img.tag.assert_called_once_with('myrepo', 'latest')


def test_build_nonzero_exit_raises_and_logs_output(monkeypatch):
    # Arrange: process returns non-zero and produces output; build should raise CalledProcessError
    img = Mock()
    img.tag = Mock()
    docker_client = make_docker_client(version='19.03.12', components=None, image_obj=img)

    monkeypatch.setattr('openhands.runtime.builder.docker.docker.from_env', lambda: docker_client)

    builder = DockerRuntimeBuilder(docker_client)

    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder.check_buildx', staticmethod(lambda is_podman=False: True))

    fake_proc = FakeProcess(lines=['error line 1\n', 'error line 2\n', ''], return_code=2)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: fake_proc)

    tags = ['repo:badhash']

    # Act / Assert
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        builder.build(path='.', tags=tags)

    # The exception should contain the returncode we set
    assert excinfo.value.returncode == 2
    # The output should contain the collected lines
    assert 'error line 1' in (excinfo.value.output or '')


def test_build_nonzero_no_stdout_uses_rolling_logger(monkeypatch):
    # Arrange: process has no stdout and returns non-zero; rolling_logger has content -> triggers logging branch
    img = Mock()
    img.tag = Mock()
    docker_client = make_docker_client(version='19.03.12', components=None, image_obj=img)

    monkeypatch.setattr('openhands.runtime.builder.docker.docker.from_env', lambda: docker_client)

    builder = DockerRuntimeBuilder(docker_client)

    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder.check_buildx', staticmethod(lambda is_podman=False: True))

    # Process with stdout=None
    fake_proc = FakeProcess(lines=None, return_code=1)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: fake_proc)

    # Simulate rolling logger content and enabled state
    builder.rolling_logger.all_lines = 'previous build logs...'
    builder.rolling_logger.is_enabled = lambda: True

    tags = ['repo:also_bad']

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        builder.build(path='.', tags=tags)

    assert excinfo.value.returncode == 1


def test_build_download_apt_get_failure_raises_and_logged(monkeypatch):
    # Arrange: check_buildx returns False so apt-get commands are run; simulate subprocess.run raising CalledProcessError
    img = Mock()
    img.tag = Mock()
    docker_client = make_docker_client(version='19.03.12', components=None, image_obj=img)

    monkeypatch.setattr('openhands.runtime.builder.docker.docker.from_env', lambda: docker_client)

    builder = DockerRuntimeBuilder(docker_client)

    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder.check_buildx', staticmethod(lambda is_podman=False: False))

    def fake_run_fail(*a, **k):
        raise subprocess.CalledProcessError(returncode=5, cmd='apt-get', output='apt-get failed')

    monkeypatch.setattr('subprocess.run', fake_run_fail)

    tags = ['repo:will_fail']

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        builder.build(path='.', tags=tags)

    assert excinfo.value.returncode == 5


def test_build_popen_file_not_found_and_permission_and_timeout(monkeypatch):
    # Arrange: test FileNotFoundError during Popen
    img = Mock()
    img.tag = Mock()
    docker_client = make_docker_client(version='19.03.12', components=None, image_obj=img)

    monkeypatch.setattr('openhands.runtime.builder.docker.docker.from_env', lambda: docker_client)

    builder = DockerRuntimeBuilder(docker_client)
    monkeypatch.setattr('openhands.runtime.builder.docker.DockerRuntimeBuilder.check_buildx', staticmethod(lambda is_podman=False: True))

    # FileNotFoundError
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError('no python')))
    with pytest.raises(FileNotFoundError):
        builder.build(path='.', tags=['repo:fnf'])

    # PermissionError
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: (_ for _ in ()).throw(PermissionError('denied')))
    with pytest.raises(PermissionError):
        builder.build(path='.', tags=['repo:perm'])

    # TimeoutExpired from wait()
    fake_proc_timeout = FakeProcess(lines=['line\n', ''], wait_exception=subprocess.TimeoutExpired(cmd='docker', timeout=10))
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: fake_proc_timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        builder.build(path='.', tags=['repo:timeout'])


def test_constructor_raises_on_old_docker_and_podman_versions():
    # Docker version too old should raise AgentRuntimeBuildError
    old_docker_client = make_docker_client(version='17.06', components=None)
    with pytest.raises(AgentRuntimeBuildError):
        DockerRuntimeBuilder(old_docker_client)

    # Podman too old should raise AgentRuntimeBuildError
    podman_components = [{'Name': 'Podman'}]
    old_podman_client = make_docker_client(version='4.8', components=podman_components)
    with pytest.raises(AgentRuntimeBuildError):
        DockerRuntimeBuilder(old_podman_client)
