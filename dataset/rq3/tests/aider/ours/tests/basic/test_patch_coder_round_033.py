import pytest

from aider.coders.patch_coder import (
    PatchCoder,
    PatchAction,
    Chunk,
    ActionType,
    DiffError,
)


def test_non_update_action_round_033():
    """If action.type is not UPDATE, _apply_update should raise a DiffError."""
    action = PatchAction(type=ActionType.ADD, path="some/path")
    with pytest.raises(DiffError) as exc:
        # method does not use `self`, so pass None for deterministic direct call
        PatchCoder._apply_update(None, "line1\n", action, "some/path")
    assert "_apply_update called with non-update action" in str(exc.value)


def test_overlapping_chunks_round_033():
    """Two chunks that overlap (second chunk starts before the first finishes)
    should raise a DiffError about overlapping/out-of-order chunks.
    """
    # Original content has four lines
    text = "l0\nl1\nl2\nl3\n"

    # First chunk deletes lines l1 and l2 (indices 1 and 2)
    chunk1 = Chunk(orig_index=1, del_lines=["l1", "l2"], ins_lines=[])
    # Second chunk declared to start at index 2; after chunk1 is applied
    # current_orig_line_idx will be 1 + 2 = 3, so chunk2.orig_index (2) < 3 -> overlap
    chunk2 = Chunk(orig_index=2, del_lines=[], ins_lines=["X"]) 

    action = PatchAction(type=ActionType.UPDATE, path="p", chunks=[chunk1, chunk2])

    with pytest.raises(DiffError) as exc:
        PatchCoder._apply_update(None, text, action, "p")
    assert "Overlapping or out-of-order chunk detected." in str(exc.value)


def test_mismatch_deleted_lines_round_033():
    """When the chunk's del_lines do not match the original file lines
    a DiffError with a helpful message should be raised, showing expected
    and actual lines.
    """
    text = "original_line\n"
    # Chunk expects to delete a different line than actually present
    chunk = Chunk(orig_index=0, del_lines=["expected_line"], ins_lines=[])
    action = PatchAction(type=ActionType.UPDATE, path="p", chunks=[chunk])

    with pytest.raises(DiffError) as exc:
        PatchCoder._apply_update(None, text, action, "p")
    msg = str(exc.value)
    # Message should indicate mismatch and show the expected and found lines
    assert "Mismatch applying patch near line" in msg
    assert "- expected_line" in msg
    assert "  original_line" in msg


def test_successful_update_preserves_lines_and_trailing_newline_round_033():
    """A standard update replacing a middle line should produce the
    expected joined content and include a trailing newline.
    """
    text = "a\nb\nc\n"
    chunk = Chunk(orig_index=1, del_lines=["b"], ins_lines=["B"])  # replace b -> B
    action = PatchAction(type=ActionType.UPDATE, path="p", chunks=[chunk])

    result = PatchCoder._apply_update(None, text, action, "p")
    # Expect lines: a, B, c and a single trailing newline
    assert result == "a\nB\nc\n"


def test_empty_original_and_no_chunks_returns_empty_round_033():
    """If the original text is empty and there are no chunks, the result
    should be the empty string (no added newline).
    """
    text = ""
    action = PatchAction(type=ActionType.UPDATE, path="p", chunks=[])

    result = PatchCoder._apply_update(None, text, action, "p")
    assert result == ""
