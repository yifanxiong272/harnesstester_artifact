import pytest
from aider.coders.editblock_coder import find_similar_lines


def test_no_loop_returns_empty_round_055():
    # search is longer than content -> loop body never runs -> best_ratio stays 0 -> below threshold
    search = "a\nb\nc"
    content = "a\nb"

    res = find_similar_lines(search, content)
    assert res == "", "Expected empty string when content is shorter than search (no possible chunk)"


def test_exact_match_returns_chunk_round_055():
    # content contains an exact subsequence equal to search -> should return that exact joined chunk
    search = "line1\nline2\nline3"
    # place the exact chunk in the middle of other lines
    content = "top\nline1\nline2\nline3\nbottom"

    res = find_similar_lines(search, content)
    # Should return the exact matched block, not surrounding lines
    assert res == "line1\nline2\nline3"


def test_partial_match_expansion_clamps_round_055():
    # Create a search block with length 5 and a content where a similar chunk (only middle items match)
    # is at index 1. Use a low threshold so partial matches are accepted and expansion logic runs.
    search = "A\nB\nC\nD\nE"
    content_lines = [
        "pre0",
        "x",
        "B",
        "C",
        "D",
        "y",
        "post1",
        "post2",
        "post3",
    ]
    content = "\n".join(content_lines)

    # Use a low threshold to allow the partial match (middle three items) to be considered best.
    res = find_similar_lines(search, content, threshold=0.2)

    # Because best_match_i is 1 and N=5, best_match_i - N is negative -> clamped to 0
    # best_match_end = min(len(content_lines), best_match_i + len(search_lines) + N)
    # With our values this becomes min(9, 1 + 5 + 5) = 9 -> returns the expanded window from 0:9
    expected = "\n".join(content_lines[0:9])
    assert res == expected
