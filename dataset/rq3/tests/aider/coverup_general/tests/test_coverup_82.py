# file: aider/repomap.py:787-795
# asked: {"lines": [788, 789, 791, 792, 793, 794, 795], "branches": [[788, 789], [788, 791], [792, 793], [792, 795], [793, 792], [793, 794]]}
# gained: {"lines": [788, 789, 791, 792, 793, 794, 795], "branches": [[788, 789], [788, 791], [792, 793], [792, 795], [793, 792], [793, 794]]}

import os
from pathlib import Path

import pytest

from aider.repomap import find_src_files


def test_find_src_files_non_dir(tmp_path):
    # Create a regular file (not a directory)
    file_path = tmp_path / "somefile.txt"
    file_path.write_text("content")

    # Pass the file path (as string) to the function; since it's not a directory,
    # the function should return a list containing the original argument.
    result = find_src_files(str(file_path))
    assert result == [str(file_path)]
    # Ensure original file still exists and was not modified
    assert file_path.exists()
    assert file_path.read_text() == "content"


def test_find_src_files_directory_with_nested_files(tmp_path):
    # Create a directory with files and a nested subdirectory with a file
    base = tmp_path / "rootdir"
    base.mkdir()

    f1 = base / "a.txt"
    f1.write_text("a")
    f2 = base / "b.txt"
    f2.write_text("b")

    sub = base / "nested"
    sub.mkdir()
    f3 = sub / "c.txt"
    f3.write_text("c")

    # Call the function with the directory path
    result = find_src_files(str(base))

    # The function should return paths to all files under the directory (any order)
    expected = {str(p) for p in (f1, f2, f3)}
    assert set(result) == expected
    assert len(result) == 3

    # Ensure all returned paths point to actual files
    for p in result:
        assert os.path.isfile(p)
