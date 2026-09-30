# file: aider/commands.py:1381-1398
# asked: {"lines": [1382, 1383, 1384, 1385, 1387, 1388, 1390, 1391, 1393, 1394, 1395, 1398], "branches": [[1383, 1384], [1383, 1393], [1384, 1383], [1384, 1385], [1386, 1384], [1386, 1390], [1393, 1394], [1393, 1398]]}
# gained: {"lines": [1382, 1383, 1384, 1385, 1387, 1388, 1390, 1391, 1393, 1394, 1395, 1398], "branches": [[1383, 1384], [1383, 1393], [1384, 1383], [1384, 1385], [1386, 1384], [1386, 1390], [1393, 1394], [1393, 1398]]}

import os
from types import SimpleNamespace
import pytest
from pathlib import Path

from aider.commands import Commands


def make_commands_capture():
    """
    Create a Commands instance without calling its __init__,
    and attach minimal coder and io attributes for testing.
    Returns (cmd_instance, outputs_list)
    """
    cmd = object.__new__(Commands)
    outputs = []

    def tool_output(msg):
        outputs.append(msg)

    cmd.io = SimpleNamespace(tool_output=tool_output)
    # coder has two sets as expected by the method
    cmd.coder = SimpleNamespace(abs_fnames=set(), abs_read_only_fnames=set())
    return cmd, outputs


def write_file(path: Path, content: str = "data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_add_read_only_directory_adds_files(tmp_path):
    # Create directory structure with two files
    base = tmp_path / "repo"
    file1 = base / "a.txt"
    file2 = base / "sub" / "b.txt"
    write_file(file1)
    write_file(file2)

    cmd, outputs = make_commands_capture()

    # Ensure both sets empty initially
    assert cmd.coder.abs_fnames == set()
    assert cmd.coder.abs_read_only_fnames == set()

    # Call the method with absolute path and a friendly original name
    cmd._add_read_only_directory(str(base), "repo")

    # Both files should have been added to abs_read_only_fnames
    expected = {str(file1), str(file2)}
    assert cmd.coder.abs_read_only_fnames == expected

    # Output should indicate 2 files were added
    assert outputs == [f"Added 2 files from directory repo to read-only files."]


def test_add_read_only_directory_no_new_files_when_already_present(tmp_path):
    # Create directory with one file
    base = tmp_path / "repo2"
    file1 = base / "only.txt"
    write_file(file1)

    cmd, outputs = make_commands_capture()

    # Prepopulate abs_read_only_fnames with the file path so it's not counted as new
    cmd.coder.abs_read_only_fnames.add(str(file1))

    # Also add a different file to abs_fnames to ensure that branch works (should be ignored)
    other = str(base / "ignored.txt")
    cmd.coder.abs_fnames.add(other)

    # Call the method
    cmd._add_read_only_directory(str(base), "repo2")

    # No new files should have been added (still only the prepopulated one)
    assert cmd.coder.abs_read_only_fnames == {str(file1)}
    # Output should indicate no new files added
    assert outputs == [f"No new files added from directory repo2."]
