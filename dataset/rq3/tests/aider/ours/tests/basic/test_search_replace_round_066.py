import importlib
import pytest

# Tests for aider.coders.search_replace.diff_lines
module_name = "aider.coders.search_replace"
mod = importlib.import_module(module_name)

class FakeDMP:
    """A minimal fake of the diff_match_patch object used by diff_lines.

    Tests configure FakeDMP.next_diff_main_result before calling diff_lines to
    control what diff_main returns. The instance records whether cleanup and
    charsToLines were called and captures the Diff_Timeout assignment.
    """
    # class-level slots to let tests access the most recent instance and set return
    last_instance = None
    next_diff_main_result = None

    def __init__(self):
        FakeDMP.last_instance = self
        self.Diff_Timeout = None
        self.diff_cleanupSemantic_called = False
        self.diff_cleanupEfficiency_called = False
        self.diff_charsToLines_called = False

    def diff_linesToChars(self, search_text, replace_text):
        # Return dummy placeholders. The real implementation is not needed;
        # we ensure diff_main will return already-resolved line strings.
        return "", "", []

    def diff_main(self, a, b, _):
        # Return whatever the test set up. Default to empty list if not set.
        return list(FakeDMP.next_diff_main_result or [])

    def diff_cleanupSemantic(self, diff_lines):
        self.diff_cleanupSemantic_called = True

    def diff_cleanupEfficiency(self, diff_lines):
        self.diff_cleanupEfficiency_called = True

    def diff_charsToLines(self, diff, mapping):
        # Mark that this was called. Tests use tuples for diff entries; this
        # method will reassign each tuple to itself to simulate in-place
        # conversion behavior.
        self.diff_charsToLines_called = True
        for i, (d, lines) in enumerate(list(diff)):
            # Ensure we write back a tuple (no-op transformation).
            diff[i] = (d, lines)


def _patch_fake(monkeypatch):
    # Replace the constructor symbol in the module with our FakeDMP class
    monkeypatch.setattr(mod, "diff_match_patch", FakeDMP)


def test_diff_lines_negative_round_066(monkeypatch):
    """Confirm negative diffs become lines prefixed with '-' and methods are called."""
    _patch_fake(monkeypatch)

    # Configure diff_main to return one negative chunk with two lines (with newlines)
    FakeDMP.next_diff_main_result = [(-1, "lineA\nlineB\n")]

    udiff = mod.diff_lines("search", "replace")

    assert udiff == ["-lineA\n", "-lineB\n"]

    inst = FakeDMP.last_instance
    assert inst is not None
    # diff_lines assigns the timeout to 5
    assert inst.Diff_Timeout == 5
    # cleanup and charsToLines should have been invoked
    assert inst.diff_cleanupSemantic_called is True
    assert inst.diff_cleanupEfficiency_called is True
    assert inst.diff_charsToLines_called is True


def test_diff_lines_positive_round_066(monkeypatch):
    """Confirm positive diffs become lines prefixed with '+' (single-line case)."""
    _patch_fake(monkeypatch)

    FakeDMP.next_diff_main_result = [(1, "onlyline\n")]

    udiff = mod.diff_lines("s", "r")

    assert udiff == ["+onlyline\n"]

    inst = FakeDMP.last_instance
    assert inst.Diff_Timeout == 5
    assert inst.diff_cleanupSemantic_called is True
    assert inst.diff_cleanupEfficiency_called is True
    assert inst.diff_charsToLines_called is True


def test_diff_lines_mixed_and_no_newline_round_066(monkeypatch):
    """Mixed ops including a chunk without trailing newline to exercise splitlines(keepends=True)."""
    _patch_fake(monkeypatch)

    # First a context (0) with newline, then a deletion without newline
    FakeDMP.next_diff_main_result = [(0, "ctxLine\n"), (-1, "deleted_line")]

    udiff = mod.diff_lines("s", "r")

    # The context line should be prefixed with a space and contain its newline;
    # the deleted_line has no trailing newline so it should appear without one.
    assert udiff == [" ctxLine\n", "-deleted_line"]

    inst = FakeDMP.last_instance
    assert inst.Diff_Timeout == 5
    assert inst.diff_cleanupSemantic_called is True
    assert inst.diff_cleanupEfficiency_called is True
    assert inst.diff_charsToLines_called is True
