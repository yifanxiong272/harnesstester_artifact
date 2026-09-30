import pytest

from aider.coders.udiff_coder import hunk_to_before_after


def test_hunk_to_before_after_mixed_ops_round_039():
    """Mixed hunk with leading ' ', '-', '+' should produce correct before/after strings.

    This covers the branch where len(line) >= 2, the op extraction path, and
    the three op branches that append to before and/or after.
    """
    hunk = [
        " unchanged_line\n",  # leading space -> context line
        "-removed_line\n",   # leading - -> before only
        "+added_line\n",     # leading + -> after only
    ]

    before, after = hunk_to_before_after(hunk)  # lines=False (default) -> strings

    # Expectation: the leading space loses its first character when returned
    # because code slices off the op character for len>=2 inputs.
    assert isinstance(before, str) and isinstance(after, str)
    assert before == "unchanged_line\nremoved_line\n"
    assert after == "unchanged_line\nadded_line\n"


def test_hunk_to_before_after_short_lines_lists_round_039():
    """Hunk entries shorter than 2 characters take the len<2 branch and are
    treated as context (op set to ' '), and when lines=True the function
    returns lists (not joined strings).
    """
    # Use single-character strings to trigger the len(line) < 2 branch
    hunk = ["-", "+", " ", ""]

    before_list, after_list = hunk_to_before_after(hunk, lines=True)

    # Because len < 2, op is forced to ' ' and the original line content is
    # preserved (not sliced). The function should therefore append each raw
    # item to both before and after lists.
    assert isinstance(before_list, list) and isinstance(after_list, list)
    assert before_list == ["-", "+", " ", ""]
    assert after_list == ["-", "+", " ", ""]


def test_hunk_to_before_after_order_and_empty_round_039():
    """Additional check: ensure ordering is preserved and empty strings are
    joined correctly when lines=False. Also covers an empty hunk input.
    """
    # Non-empty ordered input
    hunk = [" unchangedA\n", "+B\n", "-C\n"]
    before, after = hunk_to_before_after(hunk)
    assert before == "unchangedA\nC\n"
    assert after == "unchangedA\nB\n"

    # Empty hunk should return two empty strings
    empty_before, empty_after = hunk_to_before_after([], lines=False)
    assert empty_before == ""
    assert empty_after == ""
