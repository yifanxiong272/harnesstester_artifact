import os
from types import SimpleNamespace
import pathlib
import openhands.runtime.impl.docker.docker_runtime as drv


def _make_instance(volumes, container_name="ctn"):
    """Create a DockerRuntime-like instance without calling its constructor.

    Only the attributes accessed by _process_overlay_mounts are provided.
    """
    inst = object.__new__(drv.DockerRuntime)
    inst.container_name = container_name
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(volumes=volumes))
    return inst


def _extract_mount_attr(mount, candidates):
    """Robustly extract an attribute from Mount across docker SDK versions.

    Try attribute access, then dict-like access, then namedtuple _asdict, then repr fallback.
    """
    # try attribute names
    for name in candidates:
        if hasattr(mount, name):
            return getattr(mount, name)
    # dict-like
    try:
        for name in candidates:
            if isinstance(mount, dict) and name in mount:
                return mount[name]
            if hasattr(mount, "get") and mount.get(name) is not None:
                return mount.get(name)
    except Exception:
        pass
    # namedtuple
    if hasattr(mount, "_asdict"):
        d = mount._asdict()
        for name in candidates:
            if name in d:
                return d[name]
    # last resort: search repr string for meaningful substring
    rep = repr(mount)
    for name in candidates:
        if name in rep:
            return rep
    return None


def test_no_volumes_round_043():
    # When sandbox.volumes is None, the function should return an empty list
    inst = _make_instance(None, container_name="no_vols")
    os.environ.pop("SANDBOX_VOLUME_OVERLAYS", None)
    res = drv.DockerRuntime._process_overlay_mounts(inst)
    assert isinstance(res, list)
    assert res == []


def test_missing_overlay_base_skips_processing_round_043(monkeypatch):
    # If the SANDBOX_VOLUME_OVERLAYS env var is unset, no overlay mounts are produced
    inst = _make_instance("/abs/host:/container:overlay", container_name="no_base")
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)
    res = drv.DockerRuntime._process_overlay_mounts(inst)
    assert res == []


def test_relative_and_malformed_mounts_skipped_round_043(tmp_path, monkeypatch):
    # A relative host path should be ignored, and malformed mount specs (no colon)
    # should be skipped without raising.
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(tmp_path))
    mounts = "relative/host:/container:overlay,no_colon_entry"
    inst = _make_instance(mounts, container_name="rel_and_bad")
    res = drv.DockerRuntime._process_overlay_mounts(inst)
    # Both entries are skipped -> empty result
    assert res == []


def test_creates_overlay_mount_and_dirs_round_043(tmp_path, monkeypatch):
    # Valid absolute host path and 'overlay' mode should produce a Mount with
    # expected driver config and create upper/work directories under the
    # SANDBOX_VOLUME_OVERLAYS base.
    base = tmp_path / "overlays_base"
    # create a real host directory to be used as lowerdir
    host_dir = tmp_path / "host_lower"
    host_dir.mkdir()

    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(base))

    mount_spec = f"{host_dir}:/container/mnt:overlay"
    inst = _make_instance(mount_spec, container_name="my_container")

    res = drv.DockerRuntime._process_overlay_mounts(inst)

    # One overlay mount should be returned
    assert len(res) == 1
    mount = res[0]

    # Basic Mount properties: robust extraction across SDK versions
    target = _extract_mount_attr(mount, ["target", "Target", "target_path", "destination"])
    source = _extract_mount_attr(mount, ["source", "Source", "source_path"])  # may be empty string
    mtype = _extract_mount_attr(mount, ["type", "Type"]) or _extract_mount_attr(mount, ["mode"]) 

    # If we couldn't find structured attributes, fall back to checking repr contains the container path
    if target is None:
        assert "/container/mnt" in repr(mount)
    else:
        # when present, target should equal container path or include it in repr
        if isinstance(target, str):
            assert "/container/mnt" in target
        else:
            assert "/container/mnt" in repr(target)

    # source may be empty string (anonymous volume)
    if source is not None and not isinstance(source, str):
        assert "" in repr(source)

    # type should indicate volume
    if mtype is not None:
        if isinstance(mtype, str):
            assert "volume" in mtype
        else:
            assert "volume" in repr(mtype)

    # Driver config presence and correctness: robust extraction
    driver_cfg = _extract_mount_attr(mount, ["driver_config", "DriverConfig", "driver_cfg"]) 
    opts = None
    if driver_cfg is not None:
        # driver_cfg may be an object with .options or dict-like
        opts = _extract_mount_attr(driver_cfg, ["options", "Options"]) if not isinstance(driver_cfg, str) else None

    abshost = os.path.abspath(str(host_dir))

    # If options available, validate contents; otherwise fallback to repr checks
    if isinstance(opts, dict):
        assert opts.get("type") == "overlay"
        o_opt = opts.get("o", "")
        assert f"lowerdir={abshost}" in o_opt
        assert "upperdir=" in o_opt and "workdir=" in o_opt
    else:
        # fallback: ensure repr contains lowerdir and mentions upperdir/workdir markers
        rep = repr(mount)
        assert f"lowerdir={abshost}" in rep or f"lowerdir={str(host_dir)}" in rep
        assert "upperdir=" in rep and "workdir=" in rep

    # Check that the created overlay upper/work directories exist
    overlay_dir = os.path.join(str(base), inst.container_name, "0")
    upper_dir = os.path.join(overlay_dir, "upper")
    work_dir = os.path.join(overlay_dir, "work")
    assert os.path.isdir(upper_dir)
    assert os.path.isdir(work_dir)
