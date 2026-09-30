import pytest

from aider.coders.editblock_coder import replace_closest_edit_distance


def test_replace_closest_edit_distance_match_round_052():
    # Construct whole_lines where a contiguous chunk equals the concatenation of part_lines
    whole_lines = ["pre", "alpha", "beta", "gamma", "post"]
    part_lines = ["alpha", "beta", "gamma"]
    part = "".join(part_lines)
    # Replacement content (list of strings) that should replace the matched chunk
    replace_lines = ["X", "Y"]

    result = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)

    # The matched chunk (alpha+beta+gamma) is at indices 1..4, so after replacement we expect:
    # whole_lines[:1] + replace_lines + whole_lines[4:] -> ["pre"] + ["X","Y"] + ["post"] -> "preXYpost"
    assert result == "preXYpost"


def test_replace_closest_edit_distance_no_match_round_052():
    # If part_lines is empty the loop range will be empty and the function should return None
    whole_lines = ["only", "unrelated"]
    part_lines = []
    part = "".join(part_lines)
    replace_lines = ["ignored"]

    result = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)

    assert result is None
