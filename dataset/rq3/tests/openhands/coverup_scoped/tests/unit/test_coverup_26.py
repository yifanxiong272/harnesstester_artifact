# file: openhands/runtime/impl/docker/docker_runtime.py:331-396
# asked: {"lines": [338, 341, 342, 345, 346, 348, 350, 352, 354, 355, 356, 357, 358, 359, 360, 363, 364, 367, 368, 369, 370, 371, 373, 374, 375, 376, 377, 378, 382, 383, 384, 385, 386, 387, 388, 389, 391, 394, 396], "branches": [[341, 342], [341, 345], [346, 348], [346, 350], [354, 355], [354, 396], [356, 357], [356, 358], [363, 364], [363, 367]]}
# gained: {"lines": [338, 341, 342, 345, 346, 350, 352, 354, 355, 356, 357, 358, 359, 360, 363, 364, 367, 368, 369, 370, 371, 373, 374, 375, 376, 377, 378, 382, 383, 384, 385, 386, 387, 388, 389, 391, 394, 396], "branches": [[341, 342], [341, 345], [346, 350], [354, 355], [354, 396], [356, 357], [356, 358], [363, 364], [363, 367]]}

import os
from types import SimpleNamespace
import shutil
import pathlib
import pytest

import importlib

# import the module under test
module_name = "openhands.runtime.impl.docker.docker_runtime"
dr = importlib.import_module(module_name)


class DummyDriverConfig:
    def __init__(self, name, options):
        self.name = name
        self.options = options


class DummyMount:
    def __init__(self, target, source, type, labels, driver_config):
        self.target = target
        self.source = source
        self.type = type
        self.labels = labels
        self.driver_config = driver_config


def make_runtime_instance(volumes_value, container_name="testcontainer"):
    """
    Create a DockerRuntime-like instance without invoking its heavy __init__.
    Only the attributes used by _process_overlay_mounts are set.
    """
    inst = object.__new__(dr.DockerRuntime)
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(volumes=volumes_value))
    inst.container_name = container_name
    return inst


def test_process_overlay_mounts_returns_empty_when_no_volumes(monkeypatch, tmp_path):
    # Ensure environment has an overlay base (should be ignored because volumes is None)
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(tmp_path / "overlays"))
    inst = make_runtime_instance(None, container_name="c1")

    # Monkeypatch Mount/DriverConfig to avoid requiring docker package structures
    monkeypatch.setattr(dr, "DriverConfig", DummyDriverConfig)
    monkeypatch.setattr(dr, "Mount", DummyMount)

    mounts = dr.DockerRuntime._process_overlay_mounts(inst)
    assert isinstance(mounts, list)
    assert mounts == []


def test_process_overlay_mounts_various_entries_creates_overlays_and_skips_invalid(monkeypatch, tmp_path):
    # Prepare overlay base dir
    overlay_base = tmp_path / "overlays"
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(overlay_base))

    # Create some host directories (absolute paths)
    host1 = tmp_path / "host1"
    host2 = tmp_path / "host2"
    host3 = tmp_path / "host3"
    host1.mkdir()
    host2.mkdir()
    host3.mkdir()

    # Build mount specs including various cases:
    # - "bad" -> len(parts) < 2 -> skipped
    # - relative path -> skipped due to not absolute
    # - host1 absolute with overlay -> should create overlay (idx 2)
    # - host2 absolute but mode 'rw' -> skipped
    # - host3 absolute with overlay -> should create overlay (idx 4)
    relative = "relative/dir"
    specs = [
        "bad",
        f"{relative}:/rel:overlay",
        f"{str(host1)}:/container1:overlay",
        f"{str(host2)}:/container2:rw",
        f"{str(host3)}:/container3:overlay",
    ]
    volumes_value = ",".join(specs)

    inst = make_runtime_instance(volumes_value, container_name="my-container-id")

    # Monkeypatch Mount/DriverConfig to simple dummies to inspect values
    monkeypatch.setattr(dr, "DriverConfig", DummyDriverConfig)
    monkeypatch.setattr(dr, "Mount", DummyMount)

    mounts = dr.DockerRuntime._process_overlay_mounts(inst)

    # Expect two overlay mounts (for host1 and host3)
    assert isinstance(mounts, list)
    assert len(mounts) == 2

    # Verify properties of each created mount and that upper/work dirs exist in expected places
    # The original method uses enumerate over mount_specs, so the indices for created mounts are 2 and 4.
    expected_indices = [2, 4]
    for mount_obj, expected_idx in zip(mounts, expected_indices):
        # target should be the container path from the spec
        assert mount_obj.source == ""  # anonymous volume
        assert mount_obj.type == "volume"
        assert mount_obj.labels["app"] == "openhands"
        assert mount_obj.labels["role"] == "worker"
        assert mount_obj.labels["container"] == inst.container_name

        # driver_config should be our DummyDriverConfig
        drv = mount_obj.driver_config
        assert isinstance(drv, DummyDriverConfig)
        # The options should include the overlay mount 'o' entry
        assert "o" in drv.options
        o_val = drv.options["o"]
        # lowerdir should point to one of the hosts we created
        assert "lowerdir=" in o_val
        assert "upperdir=" in o_val
        assert "workdir=" in o_val

        # Compute expected overlay directories
        overlay_dir = overlay_base / inst.container_name / str(expected_idx)
        expected_upper = overlay_dir / "upper"
        expected_work = overlay_dir / "work"
        assert expected_upper.exists() and expected_upper.is_dir()
        assert expected_work.exists() and expected_work.is_dir()

        # lowerdir should match one of our host paths
        lowerdir_part = [p for p in o_val.split(",") if p.startswith("lowerdir=")]
        assert len(lowerdir_part) == 1
        lowerdir = lowerdir_part[0].split("=", 1)[1]
        assert lowerdir in {str(host1), str(host3)}
        # upperdir and workdir should match the expected dirs
        assert f"upperdir={str(expected_upper)}" in o_val
        assert f"workdir={str(expected_work)}" in o_val

    # Cleanup: ensure overlay base is removed (tmp_path is removed by pytest automatically,
    # but remove any created directories explicitly to be safe)
    if overlay_base.exists():
        shutil.rmtree(str(overlay_base))
