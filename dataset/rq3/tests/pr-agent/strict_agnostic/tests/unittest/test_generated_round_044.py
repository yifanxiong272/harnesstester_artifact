import pytest
from types import SimpleNamespace
import pr_agent.algo.utils as utils


def test_find_line_number_absolute_round_044():
    """
    Exercise the branch where an absolute_position is provided and matches a line inside the patch.
    The patch below contains a hunk with start2 = 10; the first non-deleted line after the hunk
    header yields absolute positions 10, 11, 12 for successive non-deleted lines. We assert the
    function finds the line index corresponding to absolute_position=11.
    """
    patch = "\n".join([
        "@@ -1,2 +10,3 @@",
        " context line",
        "+added1",
        "+added2",
        "-removed"
    ])
    file = SimpleNamespace(filename='file.txt', patch=patch)

    position, absolute_position = utils.find_line_number_of_relevant_line_in_file(
        [file],
        relevant_file='file.txt',
        relevant_line_in_file='irrelevant',
        absolute_position=11,
    )

    # The '+added1' line is at index 2 in patch.splitlines() and corresponds to absolute position 11
    assert position == 2
    # The function should return the same absolute_position we passed in when found
    assert absolute_position == 11


def test_find_line_number_difflib_round_044():
    """
    Exercise the difflib-based matching path. Provide relevant_line_in_file that exactly matches an
    added line (including '+'). difflib.get_close_matches should find that unique line and the
    function will set relevant_line_in_file to the matched '+...' line and then locate it.
    """
    patch = "\n".join([
        "@@ -1,1 +20,1 @@",
        "+unique_added"
    ])
    file = SimpleNamespace(filename='file2.txt', patch=patch)

    position, absolute_position = utils.find_line_number_of_relevant_line_in_file(
        [file],
        relevant_file='file2.txt',
        relevant_line_in_file='+unique_added',
        absolute_position=None,
    )

    # The '+unique_added' line is at index 1 and start2 in header is 20, the first non-deleted line
    # corresponds to absolute_position == 20
    assert position == 1
    assert absolute_position == 20


def test_find_line_number_plus_context_round_044():
    """
    Exercise the branch where the provided relevant_line_in_file starts with '+' but the patch
    contains the same text as a context line (without the leading '+'). The function should strip
    the '+' and find the context line, returning its index and computed absolute position.
    """
    patch = "\n".join([
        "@@ -5,2 +30,2 @@",
        " context content",
        "+another_added"
    ])
    file = SimpleNamespace(filename='file3.txt', patch=patch)

    position, absolute_position = utils.find_line_number_of_relevant_line_in_file(
        [file],
        relevant_file='file3.txt',
        relevant_line_in_file='+context content',
        absolute_position=None,
    )

    # The context line is at index 1 and corresponds to start2 == 30
    assert position == 1
    assert absolute_position == 30
