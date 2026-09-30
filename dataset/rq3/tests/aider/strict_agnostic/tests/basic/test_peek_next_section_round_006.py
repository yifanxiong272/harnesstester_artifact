import pytest
from aider.coders.patch_coder import peek_next_section, Chunk, DiffError


def test_empty_section_raises_round_006():
    """If there are no lines at the given index, the function should raise an Empty patch section error."""
    with pytest.raises(DiffError) as exc:
        peek_next_section([], 0)
    assert "Empty patch section" in str(exc.value)


def test_terminator_eof_round_006():
    """A line that is exactly the EOF terminator should be detected and is_eof should be True; index should advance by one."""
    lines = ["*** End of File"]
    context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

    assert context_lines == []
    assert chunks == []
    assert next_index == 1
    assert is_eof is True


def test_collect_add_delete_chunks_round_006():
    """Exercise a sequence of keep -> delete -> add -> keep to ensure a Chunk is finalized when mode returns to keep."""
    lines = [" unchanged", "-line1", "+line2", " line3"]
    context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

    # All input lines consumed
    assert next_index == len(lines)
    assert is_eof is False

    # Context lines: the initial kept line, the deleted line (part of original context), and the final kept line
    assert context_lines == ["unchanged", "line1", "line3"]

    # One chunk should have been created when mode went from add/delete back to keep
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)
    # orig_index = len(context_lines_at_time_of_chunk) - len(del_lines) = 2 - 1 = 1
    assert chunk.orig_index == 1
    assert chunk.del_lines == ["line1"]
    assert chunk.ins_lines == ["line2"]


def test_invalid_prefix_raises_round_006():
    """Lines without an expected prefix should raise a DiffError about invalid line prefix."""
    with pytest.raises(DiffError) as exc:
        peek_next_section(["no_prefix"], 0)
    assert "Invalid line prefix" in str(exc.value)


def test_chunk_finalized_at_eof_round_006():
    """If the section ends while in add/delete mode, the pending chunk should be finalized at function end."""
    lines = ["-a", "+b"]
    context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

    assert next_index == 2
    assert is_eof is False

    # Deleted lines become part of the context
    assert context_lines == ["a"]

    # Pending chunk should be appended at EOF
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.orig_index == 0
    assert chunk.del_lines == ["a"]
    assert chunk.ins_lines == ["b"]
