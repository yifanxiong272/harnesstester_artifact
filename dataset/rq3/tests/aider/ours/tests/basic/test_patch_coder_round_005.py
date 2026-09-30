import importlib
import types
import pytest

mod = importlib.import_module("aider.coders.patch_coder")

def test_scope_found_exact_round_005(monkeypatch):
    """When an @@ scope is present and matches the original file exactly,
    an action with adjusted chunk.orig_index is returned and fuzz is accumulated correctly.
    """
    # Use a simple normalizer consistent with production intent
    monkeypatch.setattr(mod, "_norm", lambda s: s.strip())

    # Prepare a chunk-like object; code only reads/writes .orig_index
    chunk = types.SimpleNamespace(orig_index=5)

    # peek_next_section should return a single context block and our chunk
    def fake_peek_next_section(lines, index):
        # context_block, chunks_in_section, next_index, is_eof
        return (["ctx_line"], [chunk], 2, False)

    monkeypatch.setattr(mod, "peek_next_section", fake_peek_next_section)

    # find_context should indicate the context was found at index 1 with no fuzz
    def fake_find_context(orig_lines, context_block, start, is_eof):
        return (1, 0)

    monkeypatch.setattr(mod, "find_context", fake_find_context)

    # Build a simple patch with an @@ scope line followed by the context line and a terminator
    lines = ["@@scopeA", "ctx_line", "*** End Patch"]
    # file_content contains the scope on the second line so search starting from 0 will find it
    file_content = "line0\nscopeA\nctx_line\nend\n"

    action, returned_index, total_fuzz = mod.PatchCoder._parse_update_file_sections(
        object(), lines, 0, file_content
    )

    # Assertions: Action type, chunk adjustment, index advances, and fuzz sum
    assert action.type == mod.ActionType.UPDATE
    assert len(action.chunks) == 1
    # chunk.orig_index should have been incremented by the found_index (5 + 1)
    assert action.chunks[0].orig_index == 6
    # index should equal the next_index returned by fake_peek_next_section
    assert returned_index == 2
    # fuzz should reflect the fake_find_context returned fuzz
    assert total_fuzz == 0


def test_scope_not_found_raises_round_005(monkeypatch):
    """If a provided @@ scope cannot be located in the original file,
    the function raises DiffError that includes the scope text.
    """
    monkeypatch.setattr(mod, "_norm", lambda s: s.strip())

    # A scope that does not exist in file_content
    lines = ["@@this_scope_does_not_exist", "some ctx", "*** End Patch"]
    file_content = "alpha\nbeta\ngamma\n"

    with pytest.raises(mod.DiffError) as excinfo:
        mod.PatchCoder._parse_update_file_sections(object(), lines, 0, file_content)

    msg = str(excinfo.value)
    assert "Could not find scope context" in msg
    # ensure the missing scope name appears in the error message
    assert "this_scope_does_not_exist" in msg


def test_context_not_found_raises_round_005(monkeypatch):
    """When the context block returned by peek_next_section cannot be found
    in the original file, the function raises DiffError describing the missing context.
    """
    monkeypatch.setattr(mod, "_norm", lambda s: s.strip())

    # peek_next_section returns a context block that won't be found
    def fake_peek_next_section(lines, index):
        return (["unmatched_context_line"], [], 1, False)

    monkeypatch.setattr(mod, "peek_next_section", fake_peek_next_section)

    # find_context simulates not finding the context (-1)
    def fake_find_context(orig_lines, context_block, start, is_eof):
        return (-1, 0)

    monkeypatch.setattr(mod, "find_context", fake_find_context)

    lines = ["some other line", "unmatched_context_line", "*** End Patch"]
    file_content = "one\ntwo\nthree\n"

    with pytest.raises(mod.DiffError) as excinfo:
        mod.PatchCoder._parse_update_file_sections(object(), lines, 0, file_content)

    assert "Could not find patch context" in str(excinfo.value)
