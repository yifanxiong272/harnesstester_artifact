# file: aider/coders/patch_coder.py:96-191
# asked: {"lines": [101, 102, 103, 104, 105, 106, 108, 109, 110, 113, 114, 123, 124, 125, 126, 127, 129, 130, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 148, 151, 152, 153, 154, 156, 157, 158, 161, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 178, 183, 184, 185, 186, 188, 189, 191], "branches": [[108, 109], [108, 173], [113, 123], [113, 124], [124, 125], [124, 126], [126, 127], [126, 129], [133, 134], [133, 136], [136, 137], [136, 139], [139, 140], [139, 142], [142, 143], [142, 148], [151, 152], [151, 164], [152, 153], [152, 161], [164, 165], [164, 167], [167, 168], [167, 169], [169, 108], [169, 170], [173, 174], [173, 183], [184, 185], [184, 188], [188, 189], [188, 191]]}
# gained: {"lines": [101, 102, 103, 104, 105, 106, 108, 109, 110, 113, 114, 123, 124, 125, 126, 127, 129, 130, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 148, 151, 152, 153, 154, 156, 157, 158, 161, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 178, 183, 184, 185, 186, 188, 189, 191], "branches": [[108, 109], [108, 173], [113, 123], [113, 124], [124, 125], [124, 126], [126, 127], [126, 129], [133, 134], [133, 136], [136, 137], [136, 139], [139, 140], [139, 142], [142, 143], [142, 148], [151, 152], [151, 164], [152, 153], [164, 165], [164, 167], [167, 168], [167, 169], [169, 170], [173, 174], [173, 183], [184, 185], [184, 188], [188, 189], [188, 191]]}

import pytest

from aider.coders.patch_coder import peek_next_section, Chunk, DiffError


def test_peek_next_section_chunk_finalized_on_blank_line():
    # Lines simulate: keep, delete, add, blank (should finalize chunk), keep
    lines = [
        " context1",  # keep -> 'context1'
        "-d1",        # delete -> 'd1' (also added to context_lines)
        "+a1",        # add -> 'a1'
        "",           # blank line -> treated as keep, triggers finalization of the chunk
        " context2",  # keep -> 'context2'
    ]
    context, chunks, next_index, is_eof = peek_next_section(lines, 0)

    # Verify index consumed all lines and no EOF flagged
    assert next_index == len(lines)
    assert is_eof is False

    # Context lines should include original context, deleted line, blank line, then next context
    assert context == ["context1", "d1", "", "context2"]

    # One chunk should have been created for the delete+add pair
    assert len(chunks) == 1
    c = chunks[0]
    assert isinstance(c, Chunk)
    # orig_index = len(context_lines_at_chunk_time) - len(del_lines) = 2 - 1 = 1
    assert c.orig_index == 1
    assert c.del_lines == ["d1"]
    assert c.ins_lines == ["a1"]


def test_peek_next_section_eof_and_finalize_at_end():
    # Lines simulate: keep, delete, add, EOF marker (should finalize pending chunk and set is_eof)
    lines = [
        " context1",
        "-d1",
        "+a1",
        "*** End of File",
    ]
    context, chunks, next_index, is_eof = peek_next_section(lines, 0)

    # EOF should have been detected and index advanced past it
    assert is_eof is True
    assert next_index == len(lines)

    # Context should include the original context and deleted line (no trailing keep after chunk)
    assert context == ["context1", "d1"]

    # One chunk finalized at the end
    assert len(chunks) == 1
    c = chunks[0]
    assert c.orig_index == 1
    assert c.del_lines == ["d1"]
    assert c.ins_lines == ["a1"]


def test_peek_next_section_invalid_line_prefix_raises():
    # A line without a valid prefix and not blank should raise DiffError for invalid prefix
    lines = ["this_has_no_prefix"]
    with pytest.raises(DiffError) as excinfo:
        peek_next_section(lines, 0)
    assert "Invalid line prefix" in str(excinfo.value)


def test_peek_next_section_invalid_star_section_raises():
    # A line that starts with '***' but isn't a recognized terminator should raise DiffError
    lines = ["*** Unexpected Thing"]
    with pytest.raises(DiffError) as excinfo:
        peek_next_section(lines, 0)
    assert "Invalid patch line found in update section" in str(excinfo.value)


def test_peek_next_section_empty_section_raises_on_terminators():
    # When the first line is a section terminator (e.g., '@@' or '***'), the function should detect
    # an empty section and raise DiffError.
    for terminator in ["@@ -1,1 +1,1 @@", "***"]:
        with pytest.raises(DiffError) as excinfo:
            peek_next_section([terminator], 0)
        assert "Empty patch section found" in str(excinfo.value)
