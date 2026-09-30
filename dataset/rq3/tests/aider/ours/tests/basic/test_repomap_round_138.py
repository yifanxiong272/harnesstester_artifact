import os
import importlib

import pytest

import aider.repomap as repomap

find_src_files = repomap.find_src_files


def test_non_directory_round_138(tmp_path):
    """
    When a file path (not a directory) is passed, find_src_files should
    return a single-item list containing that path.
    """
    f = tmp_path / "some_file.txt"
    f.write_text("content")

    result = find_src_files(str(f))

    # Should return the exact input path in a list when it's not a directory
    assert result == [str(f)]


def test_directory_with_files_and_empty_subdir_round_138(tmp_path, monkeypatch):
    """
    Exercise the directory branch where os.walk yields multiple roots,
    including an empty directory (no files). We monkeypatch repomap.os.walk
    to produce a deterministic ordering and assert the returned list
    contains the joined paths in that same ordering.
    """
    root_dir = tmp_path / "proj"
    root_dir.mkdir()

    # Build deterministic fake os.walk output (root, dirs, files)
    root = str(root_dir)
    sub = os.path.join(root, "sub")
    empty = os.path.join(root, "empty")

    fake_walk = [
        (root, ["sub", "empty"], ["a.txt"]),
        (sub, [], ["b.py", "c.md"]),
        (empty, [], []),
    ]

    # Patch the os.walk used inside the module under test to be deterministic
    monkeypatch.setattr(repomap.os, "walk", lambda _dir: iter(fake_walk))

    result = find_src_files(root)

    expected = [
        os.path.join(root, "a.txt"),
        os.path.join(sub, "b.py"),
        os.path.join(sub, "c.md"),
    ]

    assert result == expected
