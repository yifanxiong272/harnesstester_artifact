# file: aider/coders/single_wholefile_func_coder.py:66-85
# asked: {"lines": [66, 67, 70, 72, 73, 74, 76, 78, 79, 80, 81, 82, 83, 85], "branches": [[73, 74], [73, 76]]}
# gained: {"lines": [66, 67, 70, 72, 73, 74, 76, 78, 79, 80, 81, 82, 83, 85], "branches": [[73, 74], [73, 76]]}

import types
import builtins
import pytest

from types import SimpleNamespace

import aider.coders.single_wholefile_func_coder as swf_module
from aider.coders.single_wholefile_func_coder import SingleWholeFileFunctionCoder


def test_live_diffs_when_no_existing_file(monkeypatch):
    # Arrange
    fname = "some/file.py"
    new_content = "hello\nworld\n"
    final_flag = False

    # Create a coder instance without running __init__
    coder = object.__new__(SingleWholeFileFunctionCoder)
    coder.abs_root_path = lambda f: f"/fake/root/{f}"

    # io.read_text should return None to exercise the branch where content is missing
    coder.io = SimpleNamespace(read_text=lambda path: None)

    # Prepare a stub for diffs.diff_partial_update that captures arguments and returns a string
    captured = {}

    def fake_diff_partial_update(orig_lines, lines, final, fname=None):
        captured['orig_lines'] = orig_lines
        captured['lines'] = lines
        captured['final'] = final
        captured['fname'] = fname
        # return a multi-line string so .splitlines() yields multiple entries
        return "DIFF_LINE_1\nDIFF_LINE_2\n"

    # Patch the diff function in the module under test
    monkeypatch.setattr(swf_module.diffs, "diff_partial_update", fake_diff_partial_update)

    # Act
    result = swf_module.SingleWholeFileFunctionCoder.live_diffs(coder, fname, new_content, final_flag)

    # Assert
    # Since io.read_text returned None, orig_lines should be []
    assert captured['orig_lines'] == []
    # lines should be the new content split with keepends=True
    assert captured['lines'] == new_content.splitlines(keepends=True)
    assert captured['final'] is final_flag
    assert captured['fname'] == fname
    # The function returns the diff lines joined by '\n' (splitlines() removes trailing empty)
    assert result == "DIFF_LINE_1\nDIFF_LINE_2"


def test_live_diffs_with_existing_content(monkeypatch):
    # Arrange
    fname = "project/module.py"
    new_content = "def foo():\n    return 1\n"
    final_flag = True

    coder = object.__new__(SingleWholeFileFunctionCoder)
    coder.abs_root_path = lambda f: f"/project/root/{f}"

    # io.read_text returns an existing file content string; splitlines() without keepends is expected
    existing_content = "def old():\n    pass\n"
    coder.io = SimpleNamespace(read_text=lambda path: existing_content)

    captured = {}

    def fake_diff_partial_update(orig_lines, lines, final, fname=None):
        captured['orig_lines'] = orig_lines
        captured['lines'] = lines
        captured['final'] = final
        captured['fname'] = fname
        # include various newline patterns
        return "A\nB\nC\n"

    monkeypatch.setattr(swf_module.diffs, "diff_partial_update", fake_diff_partial_update)

    # Act
    result = swf_module.SingleWholeFileFunctionCoder.live_diffs(coder, fname, new_content, final_flag)

    # Assert
    # orig_lines should be existing_content.splitlines() (no keepends)
    assert captured['orig_lines'] == existing_content.splitlines()
    # lines should be new_content.splitlines(keepends=True)
    assert captured['lines'] == new_content.splitlines(keepends=True)
    assert captured['final'] is final_flag
    assert captured['fname'] == fname
    assert result == "A\nB\nC"
