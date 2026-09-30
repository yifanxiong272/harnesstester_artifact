import os
from pathlib import Path
import pytest

import openhands.runtime.impl.docker.docker_runtime as dr


class _SimpleDriverConfig:
    def __init__(self, name, options):
        self.name = name
        self.options = options


class _SimpleMount:
    def __init__(self, *, target, source, type, labels, driver_config):
        # keep same attribute names used in code under test
        self.target = target
        self.source = source
        self.type = type
        self.labels = labels
        self.driver_config = driver_config


class _Sandbox:
    def __init__(self, volumes):
        self.volumes = volumes


class _Config:
    def __init__(self, volumes):
        self.sandbox = _Sandbox(volumes)


class _SelfLike:
    def __init__(self, volumes, container_name="test-container"):
        self.config = _Config(volumes)
        self.container_name = container_name


def _patch_driver_and_mount(monkeypatch):
    # Patch the module-level DriverConfig and Mount to simple inspectable types.
    monkeypatch.setattr(dr, "DriverConfig", _SimpleDriverConfig)
    monkeypatch.setattr(dr, "Mount", _SimpleMount)


def test_no_volumes_round_043(monkeypatch):
    """When sandbox.volumes is None, function returns empty list early."""
    _patch_driver_and_mount(monkeypatch)
    s = _SelfLike(volumes=None)

    # Ensure environment not required for this branch
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)

    mounts = dr.DockerRuntime._process_overlay_mounts(s)
    assert isinstance(mounts, list)
    assert mounts == []


def test_no_overlay_base_round_043(monkeypatch, tmp_path):
    """When SANDBOX_VOLUME_OVERLAYS env var is missing, returns empty list even if volumes present."""
    _patch_driver_and_mount(monkeypatch)

    # Provide volumes but do NOT set SANDBOX_VOLUME_OVERLAYS
    s = _SelfLike(volumes=f"{tmp_path / 'host'}:/mnt:overlay")
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)

    mounts = dr.DockerRuntime._process_overlay_mounts(s)
    assert mounts == []


def test_malformed_spec_round_043(monkeypatch, tmp_path):
    """Entries with fewer than 2 colon-separated parts are skipped."""
    _patch_driver_and_mount(monkeypatch)

    overlay_base = tmp_path / "overlays"
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(overlay_base))

    # 'badspec' has no colon and should be ignored
    s = _SelfLike(volumes="badspec")

    mounts = dr.DockerRuntime._process_overlay_mounts(s)
    assert mounts == []


def test_non_abs_or_no_overlay_round_043(monkeypatch, tmp_path):
    """Skips mounts where host path is not absolute or mount mode lacks 'overlay'."""
    _patch_driver_and_mount(monkeypatch)

    overlay_base = tmp_path / "overlays"
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(overlay_base))

    # relative host path (not absolute) -> skipped
    rel_spec = "relative/path:/container1:overlay"
    # absolute host but mode lacks 'overlay' -> skipped
    abs_host = tmp_path / "host_abs"
    abs_host.mkdir()
    abs_spec = f"{abs_host.as_posix()}:/container2:rw"

    s = _SelfLike(volumes=rel_spec + "," + abs_spec)

    mounts = dr.DockerRuntime._process_overlay_mounts(s)
    assert mounts == []


def test_valid_overlay_mount_round_043(monkeypatch, tmp_path):
    """A valid overlay spec produces a Mount with expected driver_config options and labels."""
    _patch_driver_and_mount(monkeypatch)

    overlay_base = tmp_path / "overlays"
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(overlay_base))

    # Create a concrete absolute host path
    host_path = tmp_path / "host_src"
    host_path.mkdir()

    container_path = "/container"
    # Provide a single valid spec
    spec = f"{host_path.as_posix()}:{container_path}:overlay"
    s = _SelfLike(volumes=spec, container_name="ctr123")

    mounts = dr.DockerRuntime._process_overlay_mounts(s)

    # Exactly one mount created
    assert isinstance(mounts, list)
    assert len(mounts) == 1

    m = mounts[0]
    # target is the container path provided
    assert m.target == container_path
    # source is anonymous as function sets ''
    assert m.source == ''
    # type is volume
    assert m.type == 'volume'

    # labels include container name
    assert isinstance(m.labels, dict)
    assert m.labels.get('container') == 'ctr123'
    assert m.labels.get('app') == 'openhands'
    assert m.labels.get('role') == 'worker'

    # driver_config captured
    assert hasattr(m, 'driver_config')
    dc = m.driver_config
    assert dc.name == 'local'
    # options must include the overlay options and a composed 'o' string
    assert isinstance(dc.options, dict)
    assert dc.options.get('type') == 'overlay'
    assert 'o' in dc.options
    o_str = dc.options['o']

    # o string must contain lowerdir pointing to the provided host_path and mention upperdir and workdir
    assert str(host_path) in o_str
    assert 'upperdir=' in o_str
    assert 'workdir=' in o_str
