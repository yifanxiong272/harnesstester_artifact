import pytest

from aider.coders.patch_coder import peek_next_section, Chunk, DiffError


def test_finalize_chunk_in_loop_round_006():
    # Sequence: keep, delete, add, keep, terminator
    lines = [" line1", "-old", "+new", " line2", "***"]

    context_lines, chunks, index, is_eof = peek_next_section(lines, 0)

    # Context lines should include the kept context and deleted lines (as original context)
    assert context_lines == ["line1", "old", "line2"]

    # One chunk should have been finalized when mode returned to 'keep'
    assert isinstance(chunks, list) and len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)

    # orig_index is len(context_lines_before_finalize) - len(del_lines)
    # At finalization time: context_lines was ['line1','old'] so orig_index == 2 - 1 == 1
    assert chunk.orig_index == 1
    assert chunk.del_lines == ["old"]
    assert chunk.ins_lines == ["new"]

    # The loop should have stopped at the terminator line index (4) and not mark EOF
    assert index == 4
    assert is_eof is False


def test_finalize_chunk_at_eof_and_detect_end_of_file_round_006():
    # Sequence: delete, add, explicit '*** End of File' terminator
    lines = ["-old", "+new", "*** End of File"]

    context_lines, chunks, index, is_eof = peek_next_section(lines, 0)

    # Deleted lines become part of context; since only '-old' before EOF, context contains 'old'
    assert context_lines == ["old"]

    # Pending chunk should be finalized at the end-of-section handling
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.orig_index == 0
    assert chunk.del_lines == ["old"]
    assert chunk.ins_lines == ["new"]

    # The function should consume the End-of-File marker and report is_eof True
    assert is_eof is True
    assert index == 3


def test_invalid_patch_line_starting_with_triple_star_raises_round_006():
    # A line starting with '***' but not exactly '***' terminator or known markers is invalid
    lines = ["*** oops"]

    with pytest.raises(DiffError) as exc:
        peek_next_section(lines, 0)

    assert "Invalid patch line found in update section" in str(exc.value)


def test_invalid_line_prefix_raises_round_006():
    # Lines without a valid prefix (+, -, ' ', or blank) should raise
    lines = ["no_prefix"]

    with pytest.raises(DiffError) as exc:
        peek_next_section(lines, 0)

    assert "Invalid line prefix in update section" in str(exc.value)


def test_blank_line_treated_as_keep_round_006():
    # Blank lines in the patch are treated as context (keep) with empty content
    lines = ["", "***"]

    context_lines, chunks, index, is_eof = peek_next_section(lines, 0)

    assert context_lines == [""]
    assert chunks == []
    assert index == 1
    assert is_eof is False
