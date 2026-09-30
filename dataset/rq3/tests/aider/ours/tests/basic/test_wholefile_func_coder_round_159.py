import importlib
from types import SimpleNamespace

import pytest

from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def test_live_diffs_none_orig_round_159(monkeypatch):
    """When io.read_text returns None, orig_lines should be an empty list and
    diff_partial_update should be called with the new content lines (with keepends).
    """
    m = importlib.import_module("aider.coders.wholefile_func_coder")

    # capture calls and the path passed to read_text
    calls = []
    read_paths = []

    def read_text(path):
        read_paths.append(path)
        return None

    # fake self with abs_root_path and io.read_text
    selfobj = SimpleNamespace(abs_root_path=lambda f: f"/abs/{f}", io=SimpleNamespace(read_text=read_text))

    def stub_diff_partial_update(orig_lines, lines, final, fname=None):
        # record arguments for assertions; convert lines to list to inspect elements
        calls.append((orig_lines, list(lines), final, fname))
        # deterministic multiline string; .splitlines() will be used by the code under test
        return "D1\nD2"

    # patch the diffs.diff_partial_update used by the module under test
    monkeypatch.setattr(m.diffs, "diff_partial_update", stub_diff_partial_update)

    # call the method under test
    result = WholeFileFunctionCoder.live_diffs(selfobj, "file.py", "a\nb\n", True)

    # oracle: returned string is the stub's string (joined exactly)
    assert result == "D1\nD2"

    # io.read_text should have been called with the absolute path
    assert read_paths == ["/abs/file.py"]

    # diff_partial_update should have been called once with expected argument shapes
    assert len(calls) == 1
    orig_lines, lines_arg, final_arg, fname_arg = calls[0]

    # when read_text returned None, orig_lines must be an empty list (branch 96->97)
    assert orig_lines == []

    # the new content lines must preserve line endings because splitlines(keepends=True) was used
    assert all(s.endswith("\n") for s in lines_arg)

    # final and fname must be propagated
    assert final_arg is True
    assert fname_arg == "file.py"


def test_live_diffs_with_orig_round_159(monkeypatch):
    """When io.read_text returns existing content, orig_lines should come from splitlines()
    and the diff_partial_update call should reflect that (branch 96->99).
    """
    m = importlib.import_module("aider.coders.wholefile_func_coder")

    calls = []

    def read_text(path):
        # existing file content (no trailing empty line)
        return "old1\nold2\n"

    # fake self with abs_root_path and io.read_text
    selfobj = SimpleNamespace(abs_root_path=lambda f: f"root/{f}", io=SimpleNamespace(read_text=read_text))

    def stub_diff_partial_update(orig_lines, lines, final, fname=None):
        calls.append((orig_lines, list(lines), final, fname))
        return "X\nY\nZ"

    monkeypatch.setattr(m.diffs, "diff_partial_update", stub_diff_partial_update)

    result = WholeFileFunctionCoder.live_diffs(selfobj, "mod.py", "new\nlines\n", False)

    # stub return value should be propagated back
    assert result == "X\nY\nZ"

    assert len(calls) == 1
    orig_lines, lines_arg, final_arg, fname_arg = calls[0]

    # orig_lines should be the existing content splitlines() (no keepends)
    assert orig_lines == ["old1", "old2"]

    # new content lines must preserve endings
    assert all(s.endswith("\n") for s in lines_arg)

    # final and fname propagated
    assert final_arg is False
    assert fname_arg == "mod.py"
