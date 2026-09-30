import os
import shutil
import tempfile
from pathlib import Path
import pytest

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime

# Helper to create an instance without running __init__
def make_runtime(runtime_initialized=True, sanitize_fn=None):
    rt = object.__new__(CLIRuntime)
    rt._runtime_initialized = runtime_initialized
    # Default sanitizer just returns the provided path
    rt._sanitize_filename = (lambda p: p) if sanitize_fn is None else sanitize_fn
    return rt


def test_runtime_not_initialized_round_021():
    rt = make_runtime(runtime_initialized=False)
    # host_src does not matter because the check for initialization happens first
    with pytest.raises(RuntimeError):
        rt.copy_to("/does/not/matter", "dest", recursive=False)


def test_copy_dir_skip_when_same_round_021():
    # Create a source directory with a file
    with tempfile.TemporaryDirectory() as parent:
        host_src = os.path.join(parent, "sourcedir")
        os.makedirs(host_src)
        src_file = os.path.join(host_src, "f.txt")
        with open(src_file, "w") as f:
            f.write("content")

        # sandbox_dest sanitized to parent: this makes final_target_dir = parent/basename(host_src) == host_src
        rt = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: parent)

        # Should complete without error and not try to copy into itself
        rt.copy_to(host_src, sandbox_dest=parent, recursive=True)

        # original file must still be present
        assert os.path.exists(src_file)
        # final target dir computed by function would equal host_src
        final_target_dir = os.path.join(parent, os.path.basename(host_src))
        assert os.path.realpath(final_target_dir) == os.path.realpath(host_src)


def test_copy_dir_recursive_round_021():
    with tempfile.TemporaryDirectory() as src_parent, tempfile.TemporaryDirectory() as dest_parent:
        host_src = os.path.join(src_parent, "sourcedir")
        os.makedirs(host_src)
        with open(os.path.join(host_src, "inner.txt"), "w") as f:
            f.write("x")

        # sanitize to dest_parent (different from src_parent)
        rt = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: dest_parent)

        rt.copy_to(host_src, sandbox_dest=dest_parent, recursive=True)

        final_target_dir = os.path.join(dest_parent, os.path.basename(host_src))
        assert os.path.isdir(final_target_dir)
        assert os.path.exists(os.path.join(final_target_dir, "inner.txt"))


def test_copy_file_scenarios_round_021():
    # Prepare a host file
    tmpdir = tempfile.mkdtemp()
    try:
        host_file = os.path.join(tmpdir, "file.txt")
        with open(host_file, "w") as f:
            f.write("hello")

        # Scenario A: sandbox_dest is an existing directory
        dest_dir = os.path.join(tmpdir, "destdir")
        os.makedirs(dest_dir)
        rtA = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: dest_dir)
        rtA.copy_to(host_file, sandbox_dest=dest_dir, recursive=False)
        copiedA = os.path.join(dest_dir, os.path.basename(host_file))
        assert os.path.exists(copiedA)
        with open(copiedA, "r") as f:
            assert f.read() == "hello"

        # Scenario B: sandbox_dest is a new directory name (no dot in basename)
        newdir = os.path.join(tmpdir, "newdir")
        # ensure it does not exist
        if os.path.exists(newdir):
            shutil.rmtree(newdir)
        rtB = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: newdir)
        rtB.copy_to(host_file, sandbox_dest=newdir, recursive=False)
        copiedB = os.path.join(newdir, os.path.basename(host_file))
        assert os.path.exists(copiedB)
        with open(copiedB, "r") as f:
            assert f.read() == "hello"

        # Scenario C: sandbox_dest is a full file path equal to source -> triggers SameFileError which should be ignored
        rtC = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: host_file)
        # Should not raise even though source and dest are identical
        rtC.copy_to(host_file, sandbox_dest=host_file, recursive=False)
        assert os.path.exists(host_file)
        with open(host_file, "r") as f:
            assert f.read() == "hello"
    finally:
        shutil.rmtree(tmpdir)


def test_copy_raises_runtime_for_unexpected_exception_round_021(monkeypatch):
    # Ensure unexpected exceptions from shutil.copy2 are translated to RuntimeError
    tmpdir = tempfile.mkdtemp()
    try:
        host_file = os.path.join(tmpdir, "file2.txt")
        with open(host_file, "w") as f:
            f.write("data")

        dest_file = os.path.join(tmpdir, "destfile.txt")

        # Monkeypatch shutil.copy2 to raise a generic Exception
        def fake_copy2(src, dst, *, follow_symlinks=True):
            raise Exception("boom")

        monkeypatch.setattr(shutil, "copy2", fake_copy2)

        rt = make_runtime(runtime_initialized=True, sanitize_fn=lambda p: dest_file)
        with pytest.raises(RuntimeError):
            rt.copy_to(host_file, sandbox_dest=dest_file, recursive=False)
    finally:
        shutil.rmtree(tmpdir)
