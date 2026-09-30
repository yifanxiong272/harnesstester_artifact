import pytest
from aider.coders import udiff_coder


def test_directly_apply_hunk_round_017(monkeypatch):
    """
    If directly_apply_hunk returns a truthy result, apply_hunk must return it immediately.
    This exercises the early-return branch (lines ~154-156).
    """
    hunk = [" context line"]

    # Provide minimal contracts for helpers used at the top of apply_hunk
    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", lambda h: ("before", "after"))
    monkeypatch.setattr(udiff_coder, "directly_apply_hunk", lambda content, h: "DIRECT_RESULT")

    res = udiff_coder.apply_hunk("ORIG_CONTENT", hunk)
    assert res == "DIRECT_RESULT"


def test_partial_hunk_success_with_trailing_nonspace_round_017(monkeypatch):
    """
    Build a hunk whose ops end with a non-space op so the code appends an extra empty section
    (hits the branch that appends [] at lines ~179-180). The apply_partial_hunk returns a
    replacement string so all_done stays True and the function returns the updated content
    (covers the main loop success path and sections construction).
    """
    # First char of each line drives ops. Use a context line (space) then a deletion (-) to
    # produce ops ' x' which ends with non-space after replacement.
    hunk = [" context1", "-deleted1"]

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", lambda h: ("b", "a"))
    monkeypatch.setattr(udiff_coder, "directly_apply_hunk", lambda content, h: None)
    monkeypatch.setattr(udiff_coder, "make_new_lines_explicit", lambda content, h: h)

    # validate the shapes received by apply_partial_hunk and return a modified content
    def fake_apply_partial_hunk(content, preceding_context, changes, following_context):
        # preconditions asserted to ensure the code divides sections as expected
        assert isinstance(preceding_context, list)
        assert isinstance(changes, list)
        assert isinstance(following_context, list)
        # ensure we received the change for this hunk
        assert any(line.startswith("-") or line.startswith("+") for line in changes)
        return "REPLACED_CONTENT"

    monkeypatch.setattr(udiff_coder, "apply_partial_hunk", fake_apply_partial_hunk)

    res = udiff_coder.apply_hunk("ORIG", hunk)
    assert res == "REPLACED_CONTENT"


def test_partial_hunk_failure_round_017(monkeypatch):
    """
    Make apply_partial_hunk return falsy so the loop detects failure and the function
    returns None (covers the failure/break branch inside the for-loop and the
    all_done False path).
    """
    hunk = [" context1", "-deleted1"]

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", lambda h: ("b", "a"))
    monkeypatch.setattr(udiff_coder, "directly_apply_hunk", lambda content, h: None)
    monkeypatch.setattr(udiff_coder, "make_new_lines_explicit", lambda content, h: h)

    # return falsy to signal failure
    monkeypatch.setattr(udiff_coder, "apply_partial_hunk", lambda content, p, c, f: None)

    res = udiff_coder.apply_hunk("ORIG", hunk)
    assert res is None
