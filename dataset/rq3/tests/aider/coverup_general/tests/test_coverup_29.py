# file: aider/coders/editblock_coder.py:296-329
# asked: {"lines": [297, 299, 300, 301, 303, 304, 305, 307, 308, 309, 310, 312, 314, 315, 316, 317, 319, 320, 322, 323, 324, 325, 327, 329], "branches": [[307, 308], [307, 319], [308, 307], [308, 309], [314, 308], [314, 315], [319, 320], [319, 322]]}
# gained: {"lines": [297, 299, 300, 301, 303, 304, 305, 307, 308, 309, 310, 312, 314, 315, 316, 317, 319, 320, 322, 323, 324, 325, 327, 329], "branches": [[307, 308], [307, 319], [308, 307], [308, 309], [314, 308], [314, 315], [319, 320], [319, 322]]}

import pytest
from aider.coders.editblock_coder import replace_closest_edit_distance


def test_replace_closest_edit_distance_exact_match():
    # whole_lines joined yields exactly part -> should be replaced
    whole_lines = ["hello", " world"]
    part_lines = ["hello", " world"]
    part = "".join(part_lines)
    replace_lines = ["REPLACED"]

    modified = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)

    assert isinstance(modified, str)
    assert modified == "REPLACED"


def test_replace_closest_edit_distance_no_sufficient_similarity():
    # No chunk close enough to part -> function should return None
    whole_lines = ["alpha", "beta", "gamma"]
    part_lines = ["completely", "different"]
    part = "unrelated_text_which_is_very_different"
    replace_lines = ["SHOULD_NOT_BE_USED"]

    modified = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)

    assert modified is None
