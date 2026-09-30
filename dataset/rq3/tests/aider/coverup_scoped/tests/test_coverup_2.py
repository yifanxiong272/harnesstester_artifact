# file: aider/coders/patch_coder.py:96-191
# asked: {"lines": [101, 102, 103, 104, 105, 106, 108, 109, 110, 113, 114, 123, 124, 125, 126, 127, 129, 130, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 148, 151, 152, 153, 154, 156, 157, 158, 161, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 178, 183, 184, 185, 186, 188, 189, 191], "branches": [[108, 109], [108, 173], [113, 123], [113, 124], [124, 125], [124, 126], [126, 127], [126, 129], [133, 134], [133, 136], [136, 137], [136, 139], [139, 140], [139, 142], [142, 143], [142, 148], [151, 152], [151, 164], [152, 153], [152, 161], [164, 165], [164, 167], [167, 168], [167, 169], [169, 108], [169, 170], [173, 174], [173, 183], [184, 185], [184, 188], [188, 189], [188, 191]]}
# gained: {"lines": [101, 102, 103, 104, 105, 106, 108, 109, 110, 113, 114, 123, 124, 126, 127, 129, 130, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 148, 151, 152, 153, 154, 156, 157, 158, 161, 164, 165, 166, 167, 168, 169, 170, 173, 183, 184, 185, 186, 188, 189, 191], "branches": [[108, 109], [108, 173], [113, 123], [113, 124], [124, 126], [126, 127], [126, 129], [133, 134], [133, 136], [136, 137], [136, 139], [139, 140], [139, 142], [142, 148], [151, 152], [151, 164], [152, 153], [164, 165], [164, 167], [167, 168], [167, 169], [169, 170], [173, 183], [184, 185], [184, 188], [188, 189], [188, 191]]}

import pytest

from aider.coders.patch_coder import peek_next_section, DiffError, Chunk


def test_chunk_creation_and_orig_index():
    # Lines simulate: keep, delete, add, delete, add, keep
    lines = [
        " keep1",
        "-old1",
        "+new1",
        "-old2",
        "+new2",
        " keep2",
    ]
    context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

    # Verify returned values
    assert is_eof is False
    assert next_index == len(lines)
    # Context lines should have had prefixes stripped; deleted lines are included in context
    assert context_lines == ["keep1", "old1", "old2", "keep2"]

    # One chunk should be created collecting both deletes and adds before returning to keep
    assert isinstance(chunks, list)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)
    assert chunk.del_lines == ["old1", "old2"]
    assert chunk.ins_lines == ["new1", "new2"]
    # orig_index should be len(context_lines_at_append) - len(del_lines) = 3 - 2 = 1
    assert chunk.orig_index == 1


def test_eof_marker_consumed_and_reported():
    # A section that is immediately an EOF marker should be recognized as EOF.
    lines = ["*** End of File"]
    context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

    assert context_lines == []
    assert chunks == []
    assert is_eof is True
    assert next_index == 1  # index should have advanced past the EOF marker


def test_invalid_three_star_line_raises_diff_error():
    # A line that starts with '***' but is not a recognized terminator should raise DiffError
    lines = ["*** Bad line"]
    with pytest.raises(DiffError) as excinfo:
        peek_next_section(lines, 0)
    assert "Invalid patch line found in update section" in str(excinfo.value)


def test_invalid_prefix_raises_diff_error():
    # Lines without valid prefix (+, -, ' ', or blank) should raise DiffError
    lines = ["no-prefix"]
    with pytest.raises(DiffError) as excinfo:
        peek_next_section(lines, 0)
    assert "Invalid line prefix in update section" in str(excinfo.value)


def test_empty_section_raises_diff_error_on_terminator():
    # If the first line is a section terminator (e.g., '@@'), the function should detect
    # an empty section and raise DiffError (unless it's an EOF marker).
    lines = ["@@ some hunk header"]
    with pytest.raises(DiffError) as excinfo:
        peek_next_section(lines, 0)
    assert "Empty patch section found." in str(excinfo.value)
