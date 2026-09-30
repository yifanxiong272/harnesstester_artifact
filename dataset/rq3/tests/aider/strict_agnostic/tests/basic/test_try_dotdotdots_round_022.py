import pytest

from aider.coders.editblock_coder import try_dotdotdots


def test_unpaired_dots_round_022():
    """When SEARCH and REPLACE have different numbers of '...' groups, a ValueError is raised."""
    whole = "whole content"
    part = "before\n...\nafter\n"  # one '...' group
    replace = "no dots here\n"  # zero '...' groups

    with pytest.raises(ValueError, match=r"Unpaired \.\.\. in SEARCH/REPLACE block"):
        try_dotdotdots(whole, part, replace)


def test_no_dots_round_022():
    """If there are no '...' markers in part, the function returns None."""
    whole = "some full text"
    part = "this part has no dots\n"
    replace = "something else\n"

    result = try_dotdotdots(whole, part, replace)
    assert result is None


def test_unmatched_dots_round_022():
    """If the literal matched '...\n' groups differ (e.g. differing leading whitespace), raise ValueError."""
    whole = "whatever"
    part = "...\n"           # matched group will be '...\n'
    replace = "   ...\n"      # matched group will be '   ...\n' (leading spaces differ)

    with pytest.raises(ValueError, match=r"Unmatched \.\.\. in SEARCH/REPLACE block"):
        try_dotdotdots(whole, part, replace)


def test_append_replace_when_part_empty_round_022():
    """When a corresponding part piece is empty and replace is non-empty, it should append (with newline if missing)."""
    whole = "start"  # does NOT end with \n
    # part with a single '...' will produce even-index pieces ['', '']
    part = "...\n"
    # replace will produce ['', 'new\n'] so pairs are ('','') and ('','new\n')
    replace = "...\nnew\n"

    result = try_dotdotdots(whole, part, replace)
    # Expect that whole had a newline appended then the replacement content
    assert result == "start\nnew\n"


def test_raise_when_part_not_found_round_022():
    """When a non-empty part piece is not present in whole at all, ValueError is raised."""
    whole = "prefix\n"  # does not contain the part piece below
    # create a single '...' so even parts are ['needle\n','']
    part = "needle\n...\n"
    replace = "needle2\n...\n"

    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)


def test_successful_replace_round_022():
    """A straightforward replacement where the part appears exactly once should return the updated whole."""
    whole = "pre\nold\n"
    # parts: ['pre\n','old\n']
    part = "pre\n...\nold\n"
    replace = "pre\n...\nnew\n"

    result = try_dotdotdots(whole, part, replace)
    assert result == "pre\nnew\n"
