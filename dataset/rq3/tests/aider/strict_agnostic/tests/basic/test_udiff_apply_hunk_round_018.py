import pytest

from aider.coders import udiff_coder as uc


def test_apply_hunk_direct_round_018(monkeypatch):
    """
    If directly_apply_hunk returns a truthy result, apply_hunk should
    return that result immediately.
    """
    # Arrange: ensure helpers return deterministic values
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: (None, None))
    monkeypatch.setattr(uc, "directly_apply_hunk", lambda content, hunk: "DIRECT_RESULT")

    # Act
    res = uc.apply_hunk("orig_content", [(" ", "line1")])

    # Assert
    assert res == "DIRECT_RESULT"


def test_apply_hunk_sectioning_all_done_round_018(monkeypatch):
    """
    Build a hunk that produces three sections: preceding_context, changes, following_context.
    Patch directly_apply_hunk to be falsy so the function proceeds to sectioning.
    Patch apply_partial_hunk to return a non-empty new content so all_done stays True and
    the final content is returned.
    """
    # Prepare a hunk that will produce sections = [[h0], [h1], [h2]]
    h0 = (" ", "before_line")
    h1 = ("-", "removed_line")
    h2 = (" ", "after_line")
    hunk = [h0, h1, h2]

    # Monkeypatch helpers
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: (None, None))
    monkeypatch.setattr(uc, "directly_apply_hunk", lambda content, h: False)
    # make_new_lines_explicit should just pass back our hunk
    monkeypatch.setattr(uc, "make_new_lines_explicit", lambda content, h: h)

    # Spy to capture arguments and return a new content to indicate success
    def fake_apply_partial_hunk(content, preceding_context, changes, following_context):
        # Validate the contexts are the lists we expect
        assert preceding_context == [h0]
        assert changes == [h1]
        assert following_context == [h2]
        return "UPDATED_CONTENT"

    monkeypatch.setattr(uc, "apply_partial_hunk", fake_apply_partial_hunk)

    # Act
    result = uc.apply_hunk("original_content", hunk)

    # Assert: apply_partial_hunk returned non-empty so apply_hunk should return that value
    assert result == "UPDATED_CONTENT"


def test_apply_hunk_partial_failure_round_018(monkeypatch):
    """
    Build a hunk that ends with a non-space op so code appends an extra empty section
    (exercising the cur_op != ' ' branch). Patch apply_partial_hunk to return falsy
    to force all_done to become False and ensure apply_hunk then returns None.
    Also assert that apply_partial_hunk was called with the expected empty following_context.
    """
    # hunk that leaves cur_op != ' ' at the end -> last op 'x' (from '-')
    h0 = (" ", "before_line")
    h1 = ("-", "removed_line")
    hunk = [h0, h1]

    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: (None, None))
    monkeypatch.setattr(uc, "directly_apply_hunk", lambda content, h: False)
    monkeypatch.setattr(uc, "make_new_lines_explicit", lambda content, h: h)

    calls = []

    def fake_apply_partial_hunk(content, preceding_context, changes, following_context):
        calls.append((preceding_context, changes, following_context))
        # Simulate failure to apply this chunk
        return None

    monkeypatch.setattr(uc, "apply_partial_hunk", fake_apply_partial_hunk)

    # Act
    result = uc.apply_hunk("orig", hunk)

    # Assert
    # When apply_partial_hunk returns falsy, apply_hunk should not return content -> None
    assert result is None

    # apply_partial_hunk should have been called once with an explicit empty following_context
    assert len(calls) == 1
    preceding_context, changes, following_context = calls[0]
    assert preceding_context == [h0]
    assert changes == [h1]
    assert following_context == []
