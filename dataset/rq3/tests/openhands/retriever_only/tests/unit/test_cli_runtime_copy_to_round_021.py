import os
import shutil
from pathlib import Path
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime

# Helper to create an instance without calling __init__
def make_runtime(runtime_initialized: bool = True):
    rt = object.__new__(CLIRuntime)
    # Minimal attributes used by copy_to
    rt._runtime_initialized = runtime_initialized
    # keep sanitize identity so tests can predict dest paths
    rt._sanitize_filename = lambda s: s
    return rt


def test_runtime_not_initialized_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=False)
    host_src = tmp_path / "nofile.txt"
    with pytest.raises(RuntimeError):
        rt.copy_to(str(host_src), str(tmp_path / "dest"), recursive=False)


def test_source_not_exists_raises_filenotfound_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=True)
    host_src = tmp_path / "does_not_exist.txt"
    # host_src does not exist -> early FileNotFoundError
    with pytest.raises(FileNotFoundError):
        rt.copy_to(str(host_src), str(tmp_path / "dest"), recursive=False)


def test_copy_file_scenario_A_trailing_slash_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=True)
    # create a real source file
    host_file = tmp_path / "source.txt"
    host_file.write_text("hello-A")

    # sandbox_dest ends with a slash -> treated as directory (Scenario A)
    sandbox_dest = str(tmp_path / "target_dir") + os.sep

    rt.copy_to(str(host_file), sandbox_dest, recursive=False)

    dest_file = Path(sandbox_dest).joinpath(host_file.name)
    assert dest_file.exists(), "Expected destination file to be created"
    assert dest_file.read_text() == "hello-A"


def test_copy_file_samefile_triggers_samefileerror_handled_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=True)
    # create a real source file
    host_file = tmp_path / "same.txt"
    host_file.write_text("original")

    # Use sandbox_dest equal to the source file path -> copy2 will attempt to copy onto itself
    # This should raise shutil.SameFileError internally but be handled (no exception propagated)
    rt.copy_to(str(host_file), str(host_file), recursive=False)

    # File should remain unchanged
    assert host_file.read_text() == "original"


def test_copy_directory_recursive_skip_when_same_target_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=True)
    # create source directory
    src_dir = tmp_path / "dir_src"
    src_dir.mkdir()
    (src_dir / "f.txt").write_text("dirfile")

    # Set sandbox_dest to parent of src_dir so final_target_dir == src_dir
    sandbox_dest = str(src_dir.parent)

    # recursive True and source and final_target_dir are identical -> should skip without error
    rt.copy_to(str(src_dir), sandbox_dest, recursive=True)

    # original files remain
    assert (src_dir / "f.txt").read_text() == "dirfile"


def test_copy_directory_recursive_copytree_round_021(tmp_path):
    rt = make_runtime(runtime_initialized=True)
    # create source directory with nested file
    src_dir = tmp_path / "dir_src2"
    src_dir.mkdir()
    (src_dir / "g.txt").write_text("gcontent")

    # choose a different dest so copytree runs
    sandbox_dest = str(tmp_path / "other_dest")

    rt.copy_to(str(src_dir), sandbox_dest, recursive=True)

    final_target_dir = Path(sandbox_dest).joinpath(src_dir.name)
    assert final_target_dir.exists() and final_target_dir.is_dir()
    assert (final_target_dir / "g.txt").read_text() == "gcontent"
