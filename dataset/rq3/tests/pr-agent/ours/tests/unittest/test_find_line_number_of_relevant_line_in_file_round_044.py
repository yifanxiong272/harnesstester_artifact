import difflib
import types

import pytest

from pr_agent.algo.utils import find_line_number_of_relevant_line_in_file


class DummyFile:
    """Minimal object with the attributes used by the function under test.
    The real code only accesses .filename and .patch, so this is sufficient.
    """

    def __init__(self, filename: str, patch: str):
        self.filename = filename
        self.patch = patch


def test_empty_diff_files_round_044():
    # When diff_files is empty, function should return the initial -1 position
    # and absolute_position should be normalized to -1 when None is passed.
    pos, abs_pos = find_line_number_of_relevant_line_in_file([], "any.py", "whatever", absolute_position=None)
    assert pos == -1
    assert abs_pos == -1


def test_absolute_position_matching_round_044():
    # Exercise the branch where absolute_position is provided (matching absolute to relative)
    # Build a patch with a hunk header where start2 == 5, then two non-removed lines so that
    # when delta == 2 the computed absolute_position_curr equals our target (6).
    patch = """@@ -1,1 +5,3 @@
 line1
+added
 another
"""
    f = DummyFile("file.py", patch)

    # absolute_position we want to match to: 6
    pos, abs_pos = find_line_number_of_relevant_line_in_file([f], "file.py", "+added", absolute_position=6)

    # The header is at index 0, 'line1' index 1, '+added' index 2 -> position should be 2
    assert pos == 2
    # absolute_position should be preserved (we supplied 6) when a match is found
    assert abs_pos == 6


def test_plus_prefix_context_search_round_044():
    # This exercises the fallback when relevant_line_in_file starts with '+' and wasn't found
    # in the previous search: the function then strips the '+' and looks for the context
    # line (without the '+') in the patch.
    patch = """@@ -2,1 +10,2 @@
 context line
+added line
"""
    f = DummyFile("file.py", patch)

    # Use a relevant_line_in_file that starts with '+' and whose underlying text
    # exists in the patch as a context line (starting with a space)
    pos, abs_pos = find_line_number_of_relevant_line_in_file([f], "file.py", "+context line", absolute_position=None)

    # header is at index 0, ' context line' is index 1
    assert pos == 1
    # start2 is 10 and delta will be 1 at that line -> absolute_position = start2 + delta - 1 = 10
    assert abs_pos == 10
