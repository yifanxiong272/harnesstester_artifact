import pytest

from aider.coders.search_replace import dmp_apply


def test_dmp_apply_remap_true_exact_replace_round_011():
    """
    Exercise the remap=True branch where a simple exact replacement should
    apply cleanly. This should traverse the remap branch, create diffs,
    create patches, optionally map patches (map_patches), apply them, and
    return the updated text when all patch applications succeed.
    """
    search_text = "hello"
    replace_text = "hi"
    original_text = "hello"

    texts = (search_text, replace_text, original_text)

    # remap=True is the default behavior; call explicitly for clarity
    result = dmp_apply(texts, remap=True)

    # Expect the exact replacement to have been applied and returned
    assert result == replace_text


def test_dmp_apply_remap_false_unapplied_patch_returns_none_round_011():
    """
    Exercise the remap=False branch where the produced patch cannot be
    applied to the provided original_text. In that case the function
    should detect not all successes and return None.
    """
    # Choose a search_text that does not appear in original_text so
    # patch_apply is expected to fail (produce False in its success list).
    search_text = "UNLIKELY_SEARCH_TOKEN"
    replace_text = "replacement"
    original_text = "this text does not contain the token"

    texts = (search_text, replace_text, original_text)

    result = dmp_apply(texts, remap=False)

    # When not all patches are applied successfully, dmp_apply returns None
    assert result is None
