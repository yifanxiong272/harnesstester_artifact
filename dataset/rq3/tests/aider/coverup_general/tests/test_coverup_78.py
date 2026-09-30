# file: aider/diffs.py:43-102
# asked: {"lines": [58, 64, 69, 84, 93, 94], "branches": [[57, 58], [63, 64], [66, 69], [75, 78], [83, 84], [86, 91], [88, 86], [92, 93]]}
# gained: {"lines": [58, 64, 69, 84, 93, 94], "branches": [[57, 58], [63, 64], [66, 69], [75, 78], [83, 84], [88, 86], [92, 93]]}

import pytest

import aider.diffs as diffs


def test_returns_empty_when_find_last_non_deleted_none(monkeypatch):
    # Arrange: make helpers no-op and find_last_non_deleted return None
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    monkeypatch.setattr(diffs, "find_last_non_deleted", lambda o, u: None)

    # Act
    result = diffs.diff_partial_update(["line1\n", "line2\n"], ["line1\n"])

    # Assert
    assert result == ""


def test_final_true_uses_num_orig_lines_and_includes_fname_and_headers(monkeypatch):
    # Arrange: ensure assert_newlines is benign
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    # When final=True, last_non_deleted is set to num_orig_lines
    monkeypatch.setattr(diffs, "create_progress_bar", lambda pct: "#" * 10)

    # Patch difflib.unified_diff to return a predictable diff that ends with a newline
    def fake_unified_diff(a, b, n=5):
        yield "--- original\n"
        yield "+++ updated\n"
        yield "@@ -1 +1 @@\n"
        yield "-old\n"
        yield "+new\n"

    monkeypatch.setattr(diffs.difflib, "unified_diff", fake_unified_diff)

    # Act
    out = diffs.diff_partial_update(["one\n", "two\n", "three\n"], ["one\n", "two\n", "three\n"], final=True, fname="test.txt")

    # Assert: should include fname headers and the diff content and fencing backticks
    expected_prefix = (chr(96) * 3) + "diff\n"
    assert out.startswith(expected_prefix)
    assert "--- test.txt original\n" in out
    assert "+++ test.txt updated\n" in out
    assert "+new\n" in out
    assert out.endswith((chr(96) * 3) + "\n\n")


def test_not_final_empty_orig_pct50_and_backticks_loop_and_adds_trailing_newline(monkeypatch):
    # Arrange: make assert_newlines a no-op
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    # For empty original, return last_non_deleted as 0 (not None)
    monkeypatch.setattr(diffs, "find_last_non_deleted", lambda o, u: 0)
    # create_progress_bar deterministic
    monkeypatch.setattr(diffs, "create_progress_bar", lambda pct: "-" * 5)

    # Build a diff body that contains 3 and 4 backticks but not 5, and has no trailing newline
    three = chr(96) * 3
    four = chr(96) * 4
    body = "+some added content with " + three + " and " + four  # no trailing newline

    def fake_unified_diff(a, b, n=5):
        yield "--- original\n"
        yield "+++ updated\n"
        yield "@@ -0,0 +1,3 @@\n"
        yield body  # intentionally no trailing newline

    monkeypatch.setattr(diffs.difflib, "unified_diff", fake_unified_diff)

    # Prepare inputs: original empty, updated must have at least one element since code replaces last element
    lines_orig = []
    lines_updated = ["placeholder\n"]

    # Act
    out = diffs.diff_partial_update(lines_orig, lines_updated, final=False, fname=None)

    # Assert:
    # backticks chosen should be five backticks because 3 and 4 are present in diff
    expected_backticks = chr(96) * 5
    assert out.startswith(expected_backticks + "diff\n")
    # The diff body we supplied did not end with newline; function should have appended one.
    assert body + "\n" in out
    # The function should end with the same number of backticks we started it with and two newlines
    assert out.endswith(expected_backticks + "\n\n")
