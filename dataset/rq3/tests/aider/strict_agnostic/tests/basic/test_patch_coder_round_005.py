import pytest

from aider.coders import patch_coder as pc


class SimpleChunk:
    def __init__(self, orig_index=0):
        self.orig_index = orig_index


def test_terminator_break_round_005():
    """If the current line is a patch terminator, the parser should break
    immediately and return an empty action, the same index, and zero fuzz."""
    lines = ["*** End Patch"]
    file_content = ""

    # Call the unbound method with a dummy self (method does not use self)
    action, new_index, total_fuzz = pc.PatchCoder._parse_update_file_sections(
        object(), lines, 0, file_content
    )

    # Observable assertions
    assert action.type == pc.ActionType.UPDATE
    assert action.chunks == []
    assert new_index == 0
    assert total_fuzz == 0


def test_context_not_found_raises_differror_round_005(monkeypatch):
    """When the context from peek_next_section cannot be found in the
    original file, the function should raise a DiffError mentioning the
    context text."""
    # Make sure there are no @@ scope lines so the scope-parsing is skipped
    lines = ["context start", "some other line"]
    file_content = "line a\nline b\n"

    # Simulate peek_next_section returning a context block and one chunk
    def fake_peek_next_section(lines_arg, index_arg):
        return ["CTX1", "CTX2"], [SimpleChunk(orig_index=0)], 2, False

    monkeypatch.setattr(pc, "peek_next_section", fake_peek_next_section)

    # Simulate find_context failing to find the context
    def fake_find_context(orig_lines, context_block, start_idx, is_eof):
        return -1, 0

    monkeypatch.setattr(pc, "find_context", fake_find_context)

    with pytest.raises(pc.DiffError) as excinfo:
        pc.PatchCoder._parse_update_file_sections(object(), lines, 0, file_content)

    # The error message should mention that it could not find the patch context
    assert "Could not find patch context" in str(excinfo.value)
    # Also assert that the context block lines are present in the message
    assert "CTX1" in str(excinfo.value) and "CTX2" in str(excinfo.value)


def test_chunk_orig_index_adjustment_and_total_fuzz_round_005(monkeypatch):
    """When find_context returns a valid found_index, the parser should
    adjust each chunk.orig_index by that found_index, append the chunk to
    action.chunks, and include any returned fuzz in total_fuzz."""
    lines = ["no terminator here"]
    # file content can be minimal; orig_lines length is not used because
    # we will monkeypatch find_context to return a found_index
    file_content = "a\nb\nc\nd\ne\n"

    # Prepare peek_next_section to return one chunk and advance index to 3
    def fake_peek_next_section(lines_arg, index_arg):
        return ["ctx_line1", "ctx_line2"], [SimpleChunk(orig_index=2)], 3, False

    monkeypatch.setattr(pc, "peek_next_section", fake_peek_next_section)

    # Simulate find_context finding the context at index 5 with fuzz 7
    def fake_find_context(orig_lines, context_block, start_idx, is_eof):
        return 5, 7

    monkeypatch.setattr(pc, "find_context", fake_find_context)

    action, new_index, total_fuzz = pc.PatchCoder._parse_update_file_sections(
        object(), lines, 0, file_content
    )

    # One chunk should be appended
    assert len(action.chunks) == 1
    # The chunk.orig_index should have been adjusted by found_index (5 + original 2)
    assert action.chunks[0].orig_index == 7
    # The returned index should equal next_index from peek_next_section (3)
    assert new_index == 3
    # The returned total_fuzz should include the fuzz value from find_context
    assert total_fuzz == 7
