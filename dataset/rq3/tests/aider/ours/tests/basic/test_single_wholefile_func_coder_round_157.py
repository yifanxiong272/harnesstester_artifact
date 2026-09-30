import types
import importlib

import pytest


def _make_instance_without_init(module):
    """Create an instance of SingleWholeFileFunctionCoder without calling __init__."""
    cls = module.SingleWholeFileFunctionCoder
    inst = object.__new__(cls)
    return inst


def test_live_diffs_orig_none_round_157(monkeypatch):
    """When io.read_text returns None, orig_lines should be [] and diff called with expected args."""
    mod = importlib.import_module("aider.coders.single_wholefile_func_coder")

    inst = _make_instance_without_init(mod)
    # abs_root_path must accept the fname and return a path (shape preserved)
    inst.abs_root_path = lambda fname: "/fake/root/" + fname
    # io.read_text returns None to exercise the branch that sets orig_lines = []
    inst.io = types.SimpleNamespace(read_text=lambda path: None)

    captured = {}

    def fake_diff_partial_update(orig_lines, lines, final, fname=None):
        # record the inputs for assertions
        captured['orig_lines'] = list(orig_lines)
        # copy the passed lines list to avoid aliasing issues
        captured['lines'] = list(lines)
        captured['final'] = final
        captured['fname'] = fname
        # return a multi-line string so .splitlines() yields multiple items
        return "line_a\nline_b"

    # Patch the diffs function where the module resolves it
    monkeypatch.setattr(mod.diffs, 'diff_partial_update', fake_diff_partial_update)

    # Provide content with keepends when splitlines(keepends=True) is used
    content = "first\nsecond\n"
    result = mod.SingleWholeFileFunctionCoder.live_diffs(inst, "example.py", content, final=False)

    # Assertions: orig_lines branch exercised (None -> empty list)
    assert captured['orig_lines'] == []
    # lines should preserve line endings because keepends=True
    assert captured['lines'] == ["first\n", "second\n"]
    assert captured['final'] is False
    assert captured['fname'] == "example.py"
    # The returned string is the joined lines from fake_diff_partial_update.splitlines()
    assert result == "line_a\nline_b"


def test_live_diffs_with_orig_content_round_157(monkeypatch):
    """When io.read_text returns text, orig_lines should be splitlines() and diff called accordingly."""
    mod = importlib.import_module("aider.coders.single_wholefile_func_coder")

    inst = _make_instance_without_init(mod)
    inst.abs_root_path = lambda fname: "/other/root/" + fname
    # io.read_text returns existing file content (no keepends expected for orig_lines)
    inst.io = types.SimpleNamespace(read_text=lambda path: "old1\nold2")

    captured = {}

    def fake_diff_partial_update(orig_lines, lines, final, fname=None):
        captured['orig_lines'] = list(orig_lines)
        captured['lines'] = list(lines)
        captured['final'] = final
        captured['fname'] = fname
        # return three lines to ensure splitlines/join behavior is exercised
        return "A\nB\nC"

    monkeypatch.setattr(mod.diffs, 'diff_partial_update', fake_diff_partial_update)

    content = "new1\nnew2\n"
    result = mod.SingleWholeFileFunctionCoder.live_diffs(inst, "other.py", content, final=True)

    # orig_lines should be produced by splitlines() without keepends
    assert captured['orig_lines'] == ["old1", "old2"]
    # lines should include keepends
    assert captured['lines'] == ["new1\n", "new2\n"]
    assert captured['final'] is True
    assert captured['fname'] == "other.py"
    # join of splitlines from "A\nB\nC" should reproduce the original multi-line string
    assert result == "A\nB\nC"
