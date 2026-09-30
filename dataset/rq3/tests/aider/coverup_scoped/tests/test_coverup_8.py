# file: aider/coders/editblock_coder.py:190-240
# asked: {"lines": [201, 203, 204, 206, 207, 209, 211, 214, 216, 217, 219, 220, 222, 223, 224, 225, 227, 228, 229, 230, 231, 233, 234, 235, 236, 238, 240], "branches": [[206, 207], [206, 209], [209, 211], [209, 214], [216, 217], [216, 219], [223, 224], [223, 240], [224, 225], [224, 227], [227, 228], [227, 233], [228, 229], [228, 230], [233, 234], [233, 235], [235, 236], [235, 238]]}
# gained: {"lines": [201, 203, 204, 206, 207, 209, 211, 214, 216, 217, 219, 220, 222, 223, 224, 225, 227, 228, 229, 230, 231, 233, 234, 235, 236, 238, 240], "branches": [[206, 207], [206, 209], [209, 211], [209, 214], [216, 217], [216, 219], [223, 224], [223, 240], [224, 225], [224, 227], [227, 228], [227, 233], [228, 229], [233, 234], [233, 235], [235, 236], [235, 238]]}

import pytest
from aider.coders.editblock_coder import try_dotdotdots


def test_returns_none_when_no_dots():
    whole = "some content\n"
    part = "no dots here\n"
    replace = "also no dots\n"
    result = try_dotdotdots(whole, part, replace)
    assert result is None


def test_unpaired_dots_raises():
    whole = "irrelevant\n"
    part = "A\n...\nB\n"
    replace = "A\nB\n"  # no dots here -> unpaired
    with pytest.raises(ValueError) as exc:
        try_dotdotdots(whole, part, replace)
    assert "Unpaired ... in SEARCH/REPLACE block" in str(exc.value)


def test_unmatched_dots_raises():
    whole = "irrelevant\n"
    # part has '...\n' (no leading spaces), replace has indented '  ...\n' -> mismatch
    part = "start\n...\nend\n"
    replace = "start\n  ...\nend\n"
    with pytest.raises(ValueError) as exc:
        try_dotdotdots(whole, part, replace)
    assert "Unmatched ... in SEARCH/REPLACE block" in str(exc.value)


def test_empty_pair_continues_no_change():
    whole = "original content\n"
    part = "...\n"
    replace = "...\n"
    # both even pieces are empty -> loop should continue and return original whole unchanged
    result = try_dotdotdots(whole, part, replace)
    assert result == whole


def test_append_replace_when_part_empty():
    whole = "hello"  # does not end with newline
    part = "...\n"
    replace = "...\nworld\n"  # even pieces: '' and 'world\n' -> append behavior
    result = try_dotdotdots(whole, part, replace)
    assert result == "hello\nworld\n"


def test_part_not_found_raises():
    whole = "this does not contain the part\n"
    part = "NONEXISTENT_PART\n...\n"
    replace = "REPLACEMENT\n...\n"
    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)


def test_part_multiple_occurrences_raises():
    whole = "prefix\nDUP\nmid\nDUP\nsuffix\n"
    part = "DUP\n...\n"
    replace = "X\n...\n"
    # 'DUP\n' occurs twice in whole -> should raise ValueError for multiple occurrences
    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)


def test_single_replacement_success():
    whole = "begin\nTARGET\nend\n"
    part = "TARGET\n...\n"
    replace = "REPLACED\n...\n"
    result = try_dotdotdots(whole, part, replace)
    assert result == "begin\nREPLACED\nend\n"
