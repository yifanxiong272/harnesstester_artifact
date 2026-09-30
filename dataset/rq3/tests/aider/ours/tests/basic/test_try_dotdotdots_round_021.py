import pytest
from aider.coders.editblock_coder import try_dotdotdots


def test_unpaired_dots_round_021():
    # part has a ... chunk, replace does not -> lengths of split lists differ
    part = "start\n...\nend\n"
    replace = "start\nend\n"

    with pytest.raises(ValueError) as exc:
        try_dotdotdots("whole", part, replace)
    assert str(exc.value) == "Unpaired ... in SEARCH/REPLACE block"


def test_no_dots_return_none_round_021():
    # neither part nor replace contain ... -> function should return None
    part = "line1\nline2\n"
    replace = "other1\nother2\n"

    result = try_dotdotdots("anything", part, replace)
    assert result is None


def test_unmatched_dots_round_021():
    # same number of ... but the matched dot-strings differ -> specific error
    part = "pre\n...\npost\n"
    # odd-indexed matched group differs (has leading spaces)
    replace = "pre\n  ...\npost\n"

    with pytest.raises(ValueError) as exc:
        try_dotdotdots("whole", part, replace)
    assert str(exc.value) == "Unmatched ... in SEARCH/REPLACE block"


def test_empty_parts_and_replace_continue_round_021():
    # both part and replace are only ... chunks producing empty even pieces -> no changes
    whole = "original content"
    part = "...\n...\n"
    replace = "...\n...\n"

    out = try_dotdotdots(whole, part, replace)
    # nothing to replace/insert — should return original whole unchanged
    assert out == whole


def test_insert_with_added_newline_round_021():
    # first pair: part empty, replace non-empty -> should append with adding newline
    whole = "baseX"  # no trailing newline triggers newline addition branch
    part = "...\nX\n"
    replace = "INS\n...\nY\n"

    result = try_dotdotdots(whole, part, replace)
    # After insertion of INS and replacement of X->Y expected final string:
    assert result == "baseY\nINS\n"


def test_insert_without_added_newline_round_021():
    # same as previous but whole already ends with newline -> no extra newline added
    whole = "baseX\n"
    part = "...\nX\n"
    replace = "INS\n...\nY\n"

    result = try_dotdotdots(whole, part, replace)
    assert result == "baseY\nINS\n"


def test_missing_part_raises_round_021():
    # part exists in the edit description but is not found in whole -> ValueError
    whole = "nothing to see here\n"
    part = "...\nNOPE\n"
    replace = "...\nREPL\n"

    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)


def test_multiple_part_occurrences_raises_round_021():
    # if the part to replace occurs more than once in whole, a ValueError is raised
    whole = "firstX\nsecondX\n"
    part = "...\nX\n"
    replace = "...\nY\n"

    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)


def test_successful_replace_round_021():
    # a clean single replacement scenario should produce the replaced whole
    whole = "hello\nTARGET\nend\n"
    part = "...\nTARGET\n"
    replace = "...\nNEW\n"

    out = try_dotdotdots(whole, part, replace)
    assert out == "hello\nNEW\nend\n"
