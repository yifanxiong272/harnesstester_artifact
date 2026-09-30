# file: aider/diffs.py:43-102
# asked: {"lines": [58, 64, 69, 84, 93, 94], "branches": [[57, 58], [63, 64], [66, 69], [75, 78], [83, 84], [86, 91], [88, 86], [92, 93]]}
# gained: {"lines": [58, 64, 69, 84, 93, 94], "branches": [[57, 58], [63, 64], [66, 69], [75, 78], [83, 84], [88, 86], [92, 93]]}

import importlib
import pytest

# Import the module under test
diffs = importlib.import_module("aider.diffs")


def test_final_with_fname_and_backticks_in_diff(monkeypatch):
    # Prepare inputs
    lines_orig = ["line1\n", "line2\n", "line3\n"]
    lines_updated = ["u1\n", "u2\n", "u3\n"]

    # Monkeypatch helpers
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    monkeypatch.setattr(diffs, "create_progress_bar", lambda pct: "###bar###")

    # Ensure unified_diff yields content that contains backticks of length 3 and 4
    def fake_unified_diff(orig, updated, n=5):
        # Return at least two header elements then our content lines.
        # Construct backtick sequences at runtime to avoid having three consecutive backticks in the source literal.
        three = "`" * 3
        four = "`" * 4
        return iter([
            "header-line-1\n",
            "header-line-2\n",
            f"some change context with {three} and {four}\n",
            "another line\n",
        ])

    monkeypatch.setattr(diffs.difflib, "unified_diff", fake_unified_diff)

    # Call with final=True so last_non_deleted becomes num_orig_lines
    out = diffs.diff_partial_update(lines_orig, lines_updated, final=True, fname="myfile.txt")

    # Should pick a backtick length that is NOT present in diff.
    # Our diff contains backticks of length 3 and 4, so the loop will pick length 5.
    expected_start = ("`" * 5) + "diff\n"
    assert out.startswith(expected_start)
    # File headers should be included
    assert f"--- myfile.txt original\n" in out
    assert f"+++ myfile.txt updated\n" in out
    # Because final=True, the progress bar is constructed but not injected into lines_updated,
    # so it should NOT appear in the output.
    assert "  3 /   3 lines [###bar###] 100%" not in out
    # The diff content we provided must be present
    assert "some change context with " in out
    # It should end with the chosen backticks and two newlines
    assert out.endswith("`" * 5 + "\n\n")


def test_find_last_non_deleted_none_returns_empty(monkeypatch):
    # If find_last_non_deleted returns None, function should return empty string
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    monkeypatch.setattr(diffs, "find_last_non_deleted", lambda a, b: None)

    lines_orig = ["a\n", "b\n"]
    lines_updated = ["c\n"]

    out = diffs.diff_partial_update(lines_orig, lines_updated, final=False, fname=None)
    assert out == ""


def test_empty_orig_pct50_and_lines_updated_modified_and_diff_missing_newline(monkeypatch):
    # Prepare: empty original triggers pct=50 path
    monkeypatch.setattr(diffs, "assert_newlines", lambda x: None)
    monkeypatch.setattr(diffs, "find_last_non_deleted", lambda a, b: 0)
    monkeypatch.setattr(diffs, "create_progress_bar", lambda pct: "barX")

    # Capture the 'updated' argument passed into unified_diff to verify lines_updated was modified
    captured = {}

    def fake_unified_diff(orig, updated, n=5):
        # Save the updated lines to captured for assertions
        captured["updated"] = list(updated)
        # Return header lines then a content line without a trailing newline to trigger newline addition
        return iter([
            "hdr1\n",
            "hdr2\n",
            "content-without-newline"  # intentionally no trailing '\n'
        ])

    monkeypatch.setattr(diffs.difflib, "unified_diff", fake_unified_diff)

    lines_orig = []
    lines_updated = ["initial\n"]

    out = diffs.diff_partial_update(lines_orig, lines_updated, final=False, fname=None)

    # Because num_orig_lines == 0, pct should be 50 and create_progress_bar was used -> bar built
    expected_bar = f" {0:3d} / {0:3d} lines [barX] {50:3.0f}%\n"
    # lines_updated should have been replaced with the bar as its only element before diff
    assert captured["updated"] == [expected_bar]
    # The returned output should include the diff content and the added newline
    assert "content-without-newline\n" in out
    # Backticks header should be the default '