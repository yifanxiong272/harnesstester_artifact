# file: openhands/runtime/impl/cli/cli_runtime.py:764-836
# asked: {"lines": [766, 767, 768, 769, 771, 773, 775, 777, 780, 781, 782, 784, 787, 788, 792, 795, 796, 797, 798, 799, 804, 805, 806, 807, 808, 814, 815, 818, 821, 822, 825, 826, 827, 828, 830, 831, 833, 834, 835, 836], "branches": [[766, 767], [766, 768], [768, 769], [768, 771], [775, 777], [775, 792], [780, 781], [780, 787], [792, 793], [792, 821], [795, 796], [795, 804], [804, 805], [804, 814]]}
# gained: {"lines": [766, 767, 768, 769, 771, 773, 775, 777, 780, 781, 782, 784, 787, 788, 792, 795, 796, 797, 798, 799, 804, 805, 806, 807, 808, 814, 815, 818, 825, 826, 827, 828, 830, 831, 833, 834, 835, 836], "branches": [[766, 767], [766, 768], [768, 769], [768, 771], [775, 777], [775, 792], [780, 781], [780, 787], [792, 793], [795, 796], [795, 804], [804, 805], [804, 814]]}

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime
from shutil import SameFileError

class DummySelf:
    def __init__(self, initialized=True):
        self._runtime_initialized = initialized

    def _sanitize_filename(self, filename: str) -> str:
        # Return path unchanged for testing
        return filename

def _call_copy_to(self_obj, host_src, sandbox_dest, recursive=False):
    # Use the class function unbound to avoid needing a full CLIRuntime instance
    return CLIRuntime.copy_to(self_obj, host_src, sandbox_dest, recursive)

def test_not_initialized_raises(tmp_path):
    d = DummySelf(initialized=False)
    src = tmp_path / "file.txt"
    src.write_text("x")
    with pytest.raises(RuntimeError):
        _call_copy_to(d, str(src), str(tmp_path / "dest"))

def test_source_not_exists_raises(tmp_path):
    d = DummySelf(initialized=True)
    nonexist = tmp_path / "no_such_file.txt"
    assert not nonexist.exists()
    with pytest.raises(FileNotFoundError):
        _call_copy_to(d, str(nonexist), str(tmp_path / "dest"))

def test_recursive_copy_skip_identical(tmp_path):
    # Create a directory src and call copy_to with dest such that final_target_dir == src
    src_dir = tmp_path / "mydir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("a")
    # dest such that os.path.join(dest, basename(src)) == src_dir
    dest = str(src_dir.parent)  # final_target_dir = dest / 'mydir' -> src_dir
    d = DummySelf(initialized=True)
    # Should not raise and should skip copying (no duplicate)
    _call_copy_to(d, str(src_dir), dest, recursive=True)
    # Ensure original file still exists and content unchanged
    assert (src_dir / "a.txt").read_text() == "a"

def test_recursive_copy_copies(tmp_path):
    # Create src dir with nested file
    src_dir = tmp_path / "srcdir"
    src_dir.mkdir()
    (src_dir / "x.txt").write_text("hello")
    dest_parent = tmp_path / "destparent"
    dest_parent.mkdir()
    d = DummySelf(initialized=True)
    # Copy recursively into dest_parent
    _call_copy_to(d, str(src_dir), str(dest_parent), recursive=True)
    # After copy, dest_parent/srcdir/x.txt should exist
    copied = dest_parent / "srcdir" / "x.txt"
    assert copied.exists()
    assert copied.read_text() == "hello"

def test_file_copy_scenario_directory_target(tmp_path):
    # Host file
    host_file = tmp_path / "host.txt"
    host_file.write_text("host")
    # destination is an existing directory
    dest_dir = tmp_path / "existing_dir"
    dest_dir.mkdir()
    d = DummySelf(initialized=True)
    _call_copy_to(d, str(host_file), str(dest_dir))
    target = dest_dir / host_file.name
    assert target.exists()
    assert target.read_text() == "host"

def test_file_copy_scenario_new_dir(tmp_path):
    host_file = tmp_path / "file2.txt"
    host_file.write_text("data")
    # dest name without dot and does not exist
    dest_dir = tmp_path / "newdir"  # basename 'newdir' has no dot
    assert not dest_dir.exists()
    d = DummySelf(initialized=True)
    _call_copy_to(d, str(host_file), str(dest_dir))
    target = dest_dir / host_file.name
    assert target.exists()
    assert target.read_text() == "data"

def test_file_copy_scenario_full_path_and_samefile_suppressed(tmp_path, monkeypatch):
    host_file = tmp_path / "afile.txt"
    host_file.write_text("same")
    d = DummySelf(initialized=True)
    # Scenario: sandbox_dest set equal to the host file path -> copy2 would be same file.
    # To reliably trigger SameFileError across platforms, monkeypatch shutil.copy2 to raise it.
    def fake_copy2(src, dst, *, follow_symlinks=True):
        raise SameFileError("same file")
    monkeypatch.setattr(shutil, "copy2", fake_copy2)
    # Should not raise because SameFileError is caught and suppressed
    _call_copy_to(d, str(host_file), str(host_file))
    # Ensure original file still there
    assert host_file.exists()
    assert host_file.read_text() == "same"

def test_copy2_raises_file_not_found_is_rethrown(tmp_path, monkeypatch):
    host_file = tmp_path / "afile2.txt"
    host_file.write_text("z")
    d = DummySelf(initialized=True)
    # Make copy2 raise FileNotFoundError to hit that except branch (which re-raises)
    def fake_copy2(src, dst, *, follow_symlinks=True):
        raise FileNotFoundError("missing during copy")
    monkeypatch.setattr(shutil, "copy2", fake_copy2)
    with pytest.raises(FileNotFoundError):
        _call_copy_to(d, str(host_file), str(tmp_path / "destfile.txt"))

def test_copy2_raises_other_exception_wrapped(tmp_path, monkeypatch):
    host_file = tmp_path / "afile3.txt"
    host_file.write_text("y")
    d = DummySelf(initialized=True)
    # Make copy2 raise a generic exception to be wrapped into RuntimeError
    def fake_copy2(src, dst, *, follow_symlinks=True):
        raise ValueError("boom")
    monkeypatch.setattr(shutil, "copy2", fake_copy2)
    with pytest.raises(RuntimeError) as excinfo:
        _call_copy_to(d, str(host_file), str(tmp_path / "destfile2.txt"))
    assert "Unexpected error copying file: boom" in str(excinfo.value)
