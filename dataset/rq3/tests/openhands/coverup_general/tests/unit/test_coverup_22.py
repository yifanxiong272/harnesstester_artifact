# file: openhands/runtime/utils/runtime_build.py:179-268
# asked: {"lines": [190, 191, 192, 194, 196, 198, 199, 200, 202, 203, 204, 205, 207, 208, 209, 211, 212, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 225, 227, 228, 231, 232, 233, 238, 239, 240, 241, 242, 243, 244, 246, 247, 249, 251, 252, 253, 254, 255, 256, 257, 258, 262, 264, 265, 268], "branches": [[203, 204], [203, 227], [214, 215], [214, 225], [231, 232], [231, 238], [238, 239], [238, 242], [242, 243], [242, 249], [252, 253], [252, 268]]}
# gained: {"lines": [190, 191, 192, 194, 196, 198, 199, 200, 202, 203, 204, 205, 207, 208, 209, 211, 212, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 225, 227, 228, 231, 232, 233, 238, 239, 240, 241, 242, 243, 244, 246, 247, 249, 251, 252, 253, 254, 255, 256, 257, 258, 262, 264, 265, 268], "branches": [[203, 204], [203, 227], [214, 215], [214, 225], [231, 232], [231, 238], [238, 239], [238, 242], [242, 243], [242, 249], [252, 253]]}

import importlib
import pytest

module_name = "openhands.runtime.utils.runtime_build"
rb_mod = importlib.import_module(module_name)


class DummyRuntimeBuilder:
    def __init__(self, exist_map):
        """
        exist_map: dict mapping image_name -> bool
        The image_exists method will accept either (name, flag) or (name,)
        and return map.get(name, False)
        """
        self.exist_map = exist_map
        self.calls = []

    def image_exists(self, name, *args):
        # record calls for assertions
        self.calls.append((name, args))
        return self.exist_map.get(name, False)


@pytest.fixture(autouse=True)
def common_monkeypatch(monkeypatch):
    """
    Patch deterministic helper functions used by build_runtime_image_in_folder
    so tests can compute expected values.
    """
    monkeypatch.setattr(
        rb_mod,
        "get_runtime_image_repo_and_tag",
        lambda base_image: ("myrepo/runtime", "ignored_tag"),
    )
    monkeypatch.setattr(rb_mod, "get_version", lambda: "0.0.1")
    monkeypatch.setattr(rb_mod, "get_hash_for_lock_files", lambda base_image, enable_browser: "LOCKHASH")
    monkeypatch.setattr(rb_mod, "get_tag_for_versioned_image", lambda base_image: "VERSIONHASH")
    monkeypatch.setattr(rb_mod, "get_hash_for_source_files", lambda: "SRC")
    yield


def make_expected_tags():
    repo = "myrepo/runtime"
    get_version = rb_mod.get_version()
    lock_tag = f"oh_v{get_version}_{rb_mod.get_hash_for_lock_files('whatever', True)}"
    versioned_tag = f"oh_v{get_version}_{rb_mod.get_tag_for_versioned_image('whatever')}"
    source_tag = f"{lock_tag}_{rb_mod.get_hash_for_source_files()}"
    hash_image_name = f"{repo}:{source_tag}"
    lock_image_name = f"{repo}:{lock_tag}"
    versioned_image_name = f"{repo}:{versioned_tag}"
    return {
        "repo": repo,
        "lock_tag": lock_tag,
        "versioned_tag": versioned_tag,
        "source_tag": source_tag,
        "hash_image_name": hash_image_name,
        "lock_image_name": lock_image_name,
        "versioned_image_name": versioned_image_name,
    }


def test_force_rebuild_dry_run_skips_build(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_calls = []
    build_calls = []

    def fake_prep_build_folder(build_folder, base_image, build_from=None, extra_deps=None, enable_browser=None):
        prep_calls.append((build_folder, base_image, build_from, extra_deps, enable_browser))

    def fake_build_sandbox_image(*args, **kwargs):
        build_calls.append((args, kwargs))

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    rb = DummyRuntimeBuilder({})  # no images exist anywhere

    # force_rebuild True but dry_run True => prep called, build NOT called
    returned = rb_mod.build_runtime_image_in_folder(
        base_image="python:3.9",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps=None,
        dry_run=True,
        force_rebuild=True,
        platform=None,
        extra_build_args=None,
        enable_browser=True,
    )

    assert returned == tags["hash_image_name"]
    # prep_build_folder should have been called once with BuildFromImageType.SCRATCH as build_from
    assert len(prep_calls) == 1
    _, base_image_arg, build_from_arg, extra_deps_arg, enable_browser_arg = prep_calls[0]
    assert build_from_arg == rb_mod.BuildFromImageType.SCRATCH
    assert enable_browser_arg is True
    # _build_sandbox_image must not have been called because dry_run True
    assert build_calls == []


def test_force_rebuild_runs_build_and_passes_expected_args(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_calls = []
    build_calls = []

    def fake_prep_build_folder(build_folder, base_image, build_from=None, extra_deps=None, enable_browser=None):
        prep_calls.append((build_folder, base_image, build_from, extra_deps, enable_browser))

    def fake_build_sandbox_image(*args, **kwargs):
        build_calls.append((args, kwargs))

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    rb = DummyRuntimeBuilder({})

    returned = rb_mod.build_runtime_image_in_folder(
        base_image="python:3.9",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps="dep1",
        dry_run=False,
        force_rebuild=True,
        platform="linux/amd64",
        extra_build_args=["--no-cache"],
        enable_browser=False,
    )

    assert returned == tags["hash_image_name"]
    # prep called with SCRATCH
    assert len(prep_calls) == 1
    _, base_image_arg, build_from_arg, extra_deps_arg, enable_browser_arg = prep_calls[0]
    assert build_from_arg == rb_mod.BuildFromImageType.SCRATCH
    assert extra_deps_arg == "dep1"
    assert enable_browser_arg is False
    # build called once and positional args order matches function signature for force_rebuild branch
    assert len(build_calls) == 1
    args, kwargs = build_calls[0]
    # args: build_folder, runtime_builder, runtime_image_repo, source_tag, lock_tag, versioned_tag, platform
    assert args[0] == tmp_path
    assert args[1] is rb
    assert args[2] == tags["repo"]
    assert args[3] == tags["source_tag"]
    assert args[4] == tags["lock_tag"]
    assert args[5] == tags["versioned_tag"]
    assert args[6] == "linux/amd64"
    assert kwargs.get("extra_build_args") == ["--no-cache"]


def test_reuse_existing_hash_image_returns_immediately(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_called = False
    build_called = False

    def fake_prep_build_folder(*args, **kwargs):
        nonlocal prep_called
        prep_called = True

    def fake_build_sandbox_image(*args, **kwargs):
        nonlocal build_called
        build_called = True

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    # Ensure image_exists returns True for the hash image when called with second arg False
    exist_map = {tags["hash_image_name"]: True}
    rb = DummyRuntimeBuilder(exist_map)

    returned = rb_mod.build_runtime_image_in_folder(
        base_image="somebase",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps=None,
        dry_run=False,
        force_rebuild=False,
    )

    assert returned == tags["hash_image_name"]
    # Should not call prep_build_folder or build since image already exists
    assert not prep_called
    assert not build_called
    # ensure runtime_builder.image_exists was called with the expected hash image and second arg False
    assert any(call[0] == tags["hash_image_name"] and call[1] == (False,) for call in rb.calls)


def test_build_from_lock_image_uses_lock_as_base_and_passes_versioned_none(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_calls = []
    build_calls = []

    def fake_prep_build_folder(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append((build_folder, base_image, build_from, extra_deps, enable_browser))

    def fake_build_sandbox_image(*args, **kwargs):
        build_calls.append((args, kwargs))

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    # make lock image exist, but not versioned or hash
    exist_map = {
        tags["lock_image_name"]: True,
        tags["versioned_image_name"]: False,
        tags["hash_image_name"]: False,
    }
    rb = DummyRuntimeBuilder(exist_map)

    returned = rb_mod.build_runtime_image_in_folder(
        base_image="origbase",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps="deps",
        dry_run=False,
        force_rebuild=False,
        enable_browser=True,
    )

    assert returned == tags["hash_image_name"]
    # prep should be called once, base_image should be set to lock_image_name
    assert len(prep_calls) == 1
    _, base_image_arg, build_from_arg, extra_deps_arg, enable_browser_arg = prep_calls[0]
    assert base_image_arg == tags["lock_image_name"]
    assert build_from_arg == rb_mod.BuildFromImageType.LOCK
    assert extra_deps_arg == "deps"
    assert enable_browser_arg is True
    # build called once and versioned_tag passed should be None since build_from != SCRATCH
    assert len(build_calls) == 1
    args, kwargs = build_calls[0]
    # In this non-force branch the function call uses named params for versioned_tag
    assert kwargs.get("versioned_tag") is None
    assert kwargs.get("platform") is None or kwargs.get("platform") == None


def test_build_from_versioned_image_uses_versioned_base(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_calls = []
    build_calls = []

    def fake_prep_build_folder(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append((build_folder, base_image, build_from, extra_deps, enable_browser))

    def fake_build_sandbox_image(*args, **kwargs):
        build_calls.append((args, kwargs))

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    # make versioned image exist, but not lock or hash
    exist_map = {
        tags["lock_image_name"]: False,
        tags["versioned_image_name"]: True,
        tags["hash_image_name"]: False,
    }
    rb = DummyRuntimeBuilder(exist_map)

    returned = rb_mod.build_runtime_image_in_folder(
        base_image="origbase2",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps=None,
        dry_run=False,
        force_rebuild=False,
        platform="linux/arm64",
        extra_build_args=[],
    )

    assert returned == tags["hash_image_name"]
    # prep should be called with versioned_image_name
    assert len(prep_calls) == 1
    _, base_image_arg, build_from_arg, extra_deps_arg, enable_browser_arg = prep_calls[0]
    assert base_image_arg == tags["versioned_image_name"]
    assert build_from_arg == rb_mod.BuildFromImageType.VERSIONED
    # build should be called and versioned_tag must be None (not SCRATCH)
    assert len(build_calls) == 1
    args, kwargs = build_calls[0]
    assert kwargs.get("versioned_tag") is None
    # ensure platform forwarded
    assert kwargs.get("platform") == "linux/arm64"


def test_build_from_scratch_non_force_tags_versioned(tmp_path, monkeypatch):
    tags = make_expected_tags()
    prep_calls = []
    build_calls = []

    def fake_prep_build_folder(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append((build_folder, base_image, build_from, extra_deps, enable_browser))

    def fake_build_sandbox_image(*args, **kwargs):
        build_calls.append((args, kwargs))

    monkeypatch.setattr(rb_mod, "prep_build_folder", fake_prep_build_folder)
    monkeypatch.setattr(rb_mod, "_build_sandbox_image", fake_build_sandbox_image)

    # none of the images exist -> should build from scratch
    exist_map = {
        tags["lock_image_name"]: False,
        tags["versioned_image_name"]: False,
        tags["hash_image_name"]: False,
    }
    rb = DummyRuntimeBuilder(exist_map)

    returned = rb_mod.build_runtime_image_in_folder(
        base_image="base3",
        runtime_builder=rb,
        build_folder=tmp_path,
        extra_deps="d",
        dry_run=False,
        force_rebuild=False,
    )

    assert returned == tags["hash_image_name"]
    # prep called and build called with versioned_tag equal to versioned_tag (since SCRATCH)
    assert len(prep_calls) == 1
    assert len(build_calls) == 1
    args, kwargs = build_calls[0]
    # In this branch versioned_tag is passed via keyword 'versioned_tag'
    assert kwargs.get("versioned_tag") == tags["versioned_tag"]
    # build_from used for prep should be SCRATCH
    _, _, build_from_arg, _, _ = prep_calls[0]
    assert build_from_arg == rb_mod.BuildFromImageType.SCRATCH
