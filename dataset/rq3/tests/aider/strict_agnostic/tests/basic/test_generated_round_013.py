import pytest

from aider.coders.search_replace import dmp_lines_apply


def test_dmp_lines_apply_success_round_013():
    """
    When search and replace are identical, no patches should be produced
    and the function should return the original text unchanged.
    """
    search = "foo\n"
    replace = "foo\n"  # identical to search -> no changes expected
    original = "original-line\n"

    result = dmp_lines_apply((search, replace, original))

    # Expect the original text to be returned when patches apply trivially
    assert isinstance(result, str)
    assert result == original


def test_dmp_lines_apply_failure_round_013():
    """
    When search differs from replace and original doesn't contain the
    search text, the patch application should fail and the function
    should return None.
    """
    search = "needle\n"
    replace = "haystack\n"
    original = "unrelated\n"

    result = dmp_lines_apply((search, replace, original))

    # If the patch cannot be applied to the original text, function returns None
    assert result is None
