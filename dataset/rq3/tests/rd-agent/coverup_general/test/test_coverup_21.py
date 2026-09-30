# file: rdagent/utils/env.py:774-838
# asked: {"lines": [778, 779, 780, 781, 782, 784, 785, 786, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 818, 819, 820, 822, 823, 825, 826, 828, 829, 831, 832, 833, 834, 835, 837, 838], "branches": [[779, 784], [779, 803], [788, 789], [788, 790], [792, 793], [792, 802], [794, 792], [794, 795], [795, 794], [795, 796], [797, 798], [797, 800], [800, 794], [800, 801], [813, 0], [813, 814], [814, 815], [814, 818], [822, 823], [822, 825], [825, 826], [825, 828], [828, 829], [828, 831]]}
# gained: {"lines": [778, 779, 780, 781, 782, 784, 785, 786, 788, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 818, 819, 820, 822, 823, 825, 826, 828, 829, 831, 832, 833, 834, 835, 837, 838], "branches": [[779, 784], [779, 803], [788, 790], [792, 793], [792, 802], [794, 792], [794, 795], [795, 794], [795, 796], [797, 798], [797, 800], [800, 801], [813, 0], [813, 814], [814, 818], [822, 823], [822, 825], [825, 826], [825, 828], [828, 829], [828, 831]]}

import json
from types import SimpleNamespace
from pathlib import Path
import pytest

from rdagent.utils import env as env_module
from rdagent.utils.env import DockerEnv, DockerConf


class FakeErrorsModule:
    class BuildError(Exception):
        pass

    class ImageNotFound(Exception):
        pass

    class APIError(Exception):
        pass


class FakeDockerModule:
    def __init__(self, client):
        self._client = client
        self.errors = FakeErrorsModule

    def from_env(self):
        return self._client


def make_fake_client_build(resp_stream, images_get_side_effect=None, pull_resp=None):
    """
    resp_stream: what client.api.build should return
    images_get_side_effect: if Exception instance, images.get will raise it; if None, succeeds
    pull_resp: iterable to return from client.api.pull
    """
    class API:
        def __init__(self, resp_stream, pull_resp):
            self._resp_stream = resp_stream
            self._pull_resp = pull_resp

        def build(self, path, tag, network_mode):
            # capture args by attaching to instance (test can inspect)
            self.last_build = dict(path=path, tag=tag, network_mode=network_mode)
            return self._resp_stream

        def pull(self, image, stream=True, decode=True):
            self.last_pull = dict(image=image, stream=stream, decode=decode)
            if isinstance(self._pull_resp, Exception):
                # simulate raising at call time (not used here)
                raise self._pull_resp
            return list(self._pull_resp)  # ensure iterable

    class Images:
        def __init__(self, side_effect):
            self._side_effect = side_effect

        def get(self, image):
            self.last_get = image
            if isinstance(self._side_effect, Exception):
                raise self._side_effect
            return {"Id": "dummy-id"}

    api = API(resp_stream, pull_resp)
    images = Images(images_get_side_effect)
    client = SimpleNamespace(api=api, images=images)
    return client


def test_prepare_build_stream_success(monkeypatch, tmp_path):
    # Build from dockerfile, resp_stream yields bytes with JSON lines containing "stream"
    dockerfile_dir = tmp_path / "docker"
    dockerfile_dir.mkdir()

    # Prepare response stream: two parts with stream entries
    part1 = b'{"stream":"Step 1/2 : FROM python:3.9\\r\\n"}\r\n'
    part2 = b'{"stream":"Step 2/2 : RUN echo hello\\r\\n"}\r\n'
    resp_stream = [part1, part2]

    # images.get should succeed (no ImageNotFound)
    fake_client = make_fake_client_build(resp_stream=resp_stream, images_get_side_effect=None, pull_resp=[])

    # Monkeypatch docker and configure conf
    fake_docker = FakeDockerModule(fake_client)
    monkeypatch.setattr(env_module, "docker", fake_docker, raising=True)

    conf = DockerConf(image="test/image:latest", mount_path="/mnt", default_entry="/bin/sh")
    conf.build_from_dockerfile = True
    conf.dockerfile_folder_path = dockerfile_dir
    fake_self = SimpleNamespace(conf=conf)

    # Call prepare - should not raise
    DockerEnv.prepare(fake_self)

    # Assert api.build was called with expected args
    assert hasattr(fake_client.api, "last_build")
    assert fake_client.api.last_build["path"] == str(dockerfile_dir)
    assert fake_client.api.last_build["tag"] == conf.image
    assert fake_client.api.last_build["network_mode"] == conf.network


def test_prepare_build_stream_error_raises_builderror(monkeypatch, tmp_path):
    # Build from dockerfile, but build emits an error JSON -> should raise BuildError
    dockerfile_dir = tmp_path / "dockererr"
    dockerfile_dir.mkdir()

    err_part = b'{"error":"build failed due to bad Dockerfile"}\r\n'
    resp_stream = [err_part]

    fake_client = make_fake_client_build(resp_stream=resp_stream, images_get_side_effect=None, pull_resp=[])
    fake_docker = FakeDockerModule(fake_client)
    monkeypatch.setattr(env_module, "docker", fake_docker, raising=True)

    conf = DockerConf(
        image="test/image:latest",
        mount_path="/mnt",
        default_entry="/bin/sh",
    )
    conf.build_from_dockerfile = True
    conf.dockerfile_folder_path = dockerfile_dir

    fake_self = SimpleNamespace(conf=conf)
    with pytest.raises(FakeErrorsModule.BuildError):
        DockerEnv.prepare(fake_self)


def test_prepare_pull_success(monkeypatch):
    # images.get raises ImageNotFound -> api.pull yields multiple layer lines to simulate progress
    # Create lines as dictionaries that the prepare method expects
    pull_lines = [
        {"id": "layer1", "status": "Downloading", "progress": "[=>    ] 50%"},
        {"id": "layer1", "status": "Pull complete"},
        {"id": "layer2", "status": "Already exists", "progress": "[======]"},
    ]

    fake_client = make_fake_client_build(resp_stream=[], images_get_side_effect=FakeErrorsModule.ImageNotFound(), pull_resp=pull_lines)
    fake_docker = FakeDockerModule(fake_client)
    monkeypatch.setattr(env_module, "docker", fake_docker, raising=True)

    conf = DockerConf(image="repo/image:tag", mount_path="/mnt", default_entry="/bin/sh")
    conf.build_from_dockerfile = False  # not building, go straight to images.get/pull
    fake_self = SimpleNamespace(conf=conf)

    # Should not raise
    DockerEnv.prepare(fake_self)

    # Assert that images.get was attempted and pull was called with expected args
    assert getattr(fake_client.images, "last_get") == conf.image
    assert getattr(fake_client.api, "last_pull")["image"] == conf.image


def test_prepare_images_get_apierror_converted_to_runtimeerror(monkeypatch):
    # images.get raises APIError -> outer except should convert to RuntimeError
    fake_client = make_fake_client_build(resp_stream=[], images_get_side_effect=FakeErrorsModule.APIError("api down"), pull_resp=[])
    fake_docker = FakeDockerModule(fake_client)
    monkeypatch.setattr(env_module, "docker", fake_docker, raising=True)

    conf = DockerConf(image="repo/bad:tag", mount_path="/mnt", default_entry="/bin/sh")
    conf.build_from_dockerfile = False
    fake_self = SimpleNamespace(conf=conf)

    with pytest.raises(RuntimeError) as excinfo:
        DockerEnv.prepare(fake_self)
    assert "api down" in str(excinfo.value)
