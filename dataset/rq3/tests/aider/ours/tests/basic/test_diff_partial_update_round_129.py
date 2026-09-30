import pytest
from aider.diffs import diff_partial_update


def test_return_empty_when_no_common_lines_round_129():
    # No unchanged (' ') lines between orig and updated -> find_last_non_deleted returns None
    lines_orig = ["a\n", "b\n"]
    lines_updated = ["c\n", "d\n"]

    result = diff_partial_update(lines_orig, lines_updated, final=False, fname=None)

    # Should return empty string when there is no last_non_deleted
    assert result == ""


def test_final_zero_lines_with_fname_and_newline_append_round_129():
    # final=True forces last_non_deleted = num_orig_lines (0 here)
    # Use an updated last line without a trailing newline to force the code path
    # that appends a trailing newline to diff (covers the diff.endswith check)
    lines_orig = []
    lines_updated = ["line1"]  # intentionally no trailing \n

    result = diff_partial_update(lines_orig, lines_updated, final=True, fname="file.txt")

    # Header/backtick block should be present
    assert result.startswith("```diff\n")
    # fname causes original/updated headers to be included
    assert "--- file.txt original\n" in result
    assert "+++ file.txt updated\n" in result
    # The function always terminates the block with backticks and two newlines
    assert result.endswith("```\n\n")


def test_not_final_handles_backticks_in_diff_and_inserts_progress_bar_round_129():
    # Create content that contains triple-backticks so the loop that chooses
    # the backtick delimiter must skip i=3 and pick a larger delimiter.
    lines_orig = ["common\n", "```code\n", "to_delete\n"]
    lines_updated = ["common\n", "```code\n", "modified\n"]

    result = diff_partial_update(lines_orig, lines_updated, final=False, fname=None)

    # Because '```' appears in the diff, the function should choose a backtick
    # delimiter longer than 3 (we expect 4 here)
    assert result.startswith("````diff\n")

    # As not final, the last element of lines_updated is replaced with the progress
    # summary bar which includes the substring ' lines [' and a percent sign
    assert " lines [" in result
    assert "%" in result

    # The common unchanged line should be included in the diff output
    assert "common\n" in result
