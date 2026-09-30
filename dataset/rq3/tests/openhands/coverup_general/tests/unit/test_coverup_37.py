# file: openhands/runtime/impl/docker/docker_runtime.py:331-396
# asked: {"lines": [338, 341, 342, 345, 346, 348, 350, 352, 354, 355, 356, 357, 358, 359, 360, 363, 364, 367, 368, 369, 370, 371, 373, 374, 375, 376, 377, 378, 382, 383, 384, 385, 386, 387, 388, 389, 391, 394, 396], "branches": [[341, 342], [341, 345], [346, 348], [346, 350], [354, 355], [354, 396], [356, 357], [356, 358], [363, 364], [363, 367]]}
# gained: {"lines": [338, 341, 342, 345, 346, 350, 352, 354, 355, 356, 357, 358, 359, 360, 363, 364, 367, 368, 369, 370, 371, 373, 374, 375, 376, 377, 378, 382, 383, 384, 385, 386, 387, 388, 389, 391, 394, 396], "branches": [[341, 342], [341, 345], [346, 350], [354, 355], [354, 396], [356, 357], [356, 358], [363, 364], [363, 367]]}

import os
import types
from types import SimpleNamespace
import pytest

import importlib

# Import the module under test
from openhands.runtime.impl.docker import docker_runtime as dr


class FakeDriverConfig:
    def __init__(self, name: str, options: dict):
        self.name = name
        self.options = options

    def __repr__(self):
        return f"FakeDriverConfig(name={self.name!r}, options={self.options!r})"


class FakeMount:
    def __init__(self, target, source, type, labels, driver_config):
        self.target = target
        self.source = source
        self.type = type
        self.labels = labels
        self.driver_config = driver_config

    def __repr__(self):
        return (
            f"FakeMount(target={self.target!r}, source={self.source!r}, "
            f"type={self.type!r}, labels={self.labels!r}, driver_config={self.driver_config!r})"
        )


def _bind_and_call_process_overlay_mounts(self_obj):
    # Bind the function to the instance and call it.
    fn = dr.DockerRuntime._process_overlay_mounts.__get__(self_obj, dr.DockerRuntime)
    return fn()


def test_process_overlay_mounts_no_volumes(monkeypatch):
    """
    When config.sandbox.volumes is None, the function should return an empty list
    and not require SANDBOX_VOLUME_OVERLAYS to be set.
    """
    # Ensure environment variable not set
    monkeypatch.delenv('SANDBOX_VOLUME_OVERLAYS', raising=False)

    # Create minimal self-like object with required attributes
    sandbox = SimpleNamespace(volumes=None)
    config = SimpleNamespace(sandbox=sandbox)
    self_obj = SimpleNamespace(config=config, container_name="testcontainer")

    # Call method
    result = _bind_and_call_process_overlay_mounts(self_obj)

    assert isinstance(result, list)
    assert result == []


def test_process_overlay_mounts_creates_overlay_mounts(tmp_path, monkeypatch):
    """
    Provide a complex volumes string to exercise all branches:
      - entries with <2 parts are skipped
      - relative host paths are skipped
      - non-overlay modes are skipped
      - absolute path with 'overlay' in mode produces a FakeMount
    Also ensure upper/work directories are created and driver_config contains correct options.
    """
    # Monkeypatch DriverConfig and Mount in the module to avoid docker dependency
    monkeypatch.setattr(dr, "DriverConfig", FakeDriverConfig, raising=True)
    monkeypatch.setattr(dr, "Mount", FakeMount, raising=True)

    # Prepare overlay base dir using tmp_path and set env var
    overlay_base = tmp_path / "overlays"
    monkeypatch.setenv('SANDBOX_VOLUME_OVERLAYS', str(overlay_base))

    # Prepare host absolute paths under tmp_path
    host_abs1 = tmp_path / "host_abs1"
    host_abs1_str = str(host_abs1)
    host_abs2 = tmp_path / "host_abs2"
    host_abs2_str = str(host_abs2)

    # Build volumes string with multiple cases:
    # 0: badentry -> len(parts)<2 -> skipped
    # 1: relative path with overlay -> skipped because not abs
    # 2: absolute path with rw -> skipped because 'overlay' not in mode
    # 3: absolute path with overlay -> should create mount
    volumes = ",".join([
        "badentry",
        "relative/path:/app:overlay",
        f"{host_abs1_str}:/container1:rw",
        f"{host_abs2_str}:/container2:overlay",
    ])

    sandbox = SimpleNamespace(volumes=volumes)
    config = SimpleNamespace(sandbox=sandbox)
    container_name = "cid123"
    self_obj = SimpleNamespace(config=config, container_name=container_name)

    # Call method
    mounts = _bind_and_call_process_overlay_mounts(self_obj)

    # Only the fourth spec should have produced a mount
    assert isinstance(mounts, list)
    assert len(mounts) == 1

    mount = mounts[0]
    # Verify mount is the FakeMount we expect
    assert isinstance(mount, FakeMount)
    assert mount.target == "/container2"
    assert mount.source == ""
    assert mount.type == "volume"
    assert mount.labels["app"] == "openhands"
    assert mount.labels["role"] == "worker"
    assert mount.labels["container"] == container_name

    # Verify driver_config contents
    driver_cfg = mount.driver_config
    assert isinstance(driver_cfg, FakeDriverConfig)
    assert driver_cfg.name == "local"
    opts = driver_cfg.options
    assert opts["type"] == "overlay"
    assert opts["device"] == "overlay"
    # lowerdir should reference the absolute host path we provided
    o_str = opts["o"]
    assert f"lowerdir={os.path.abspath(host_abs2_str)}" in o_str
    # upperdir and workdir should be inside overlay_base/container_name/<idx> directories
    # The idx is the enumeration index of the mount spec (0-based). Our overlay mount is at index 3.
    expected_overlay_dir = os.path.join(str(overlay_base), container_name, "3")
    assert f"upperdir={os.path.join(expected_overlay_dir, 'upper')}" in o_str
    assert f"workdir={os.path.join(expected_overlay_dir, 'work')}" in o_str

    # Check the directories were actually created
    upper_dir = os.path.join(expected_overlay_dir, "upper")
    work_dir = os.path.join(expected_overlay_dir, "work")
    assert os.path.isdir(upper_dir)
    assert os.path.isdir(work_dir)
