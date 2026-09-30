# file: rdagent/utils/agent/apply_patch.py:173-223
# asked: {"lines": [174, 175, 176, 177, 178, 186, 187, 188, 189, 191, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 210, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 222, 223], "branches": [[177, 186], [177, 223], [188, 189], [188, 191], [191, 192], [191, 194], [194, 195], [194, 210], [196, 197], [196, 202], [197, 198], [197, 202], [198, 197], [198, 199], [202, 203], [202, 210], [203, 204], [203, 210], [204, 203], [204, 205], [212, 213], [212, 217], [218, 219], [218, 221]]}
# gained: {"lines": [174, 175, 176, 177, 178, 186, 187, 188, 189, 191, 194, 195, 196, 197, 198, 202, 203, 204, 210, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 222, 223], "branches": [[177, 186], [177, 223], [188, 189], [188, 191], [191, 194], [194, 195], [194, 210], [196, 197], [197, 198], [197, 202], [198, 197], [202, 203], [203, 204], [203, 210], [204, 203], [212, 213], [212, 217], [218, 219], [218, 221]]}

import pytest

from types import SimpleNamespace

import rdagent.utils.agent.apply_patch as apply_patch


def make_chunk(orig_index=0):
    # Minimal chunk-like object expected by Parser._parse_update_file
    return SimpleNamespace(orig_index=orig_index)


def test_parse_update_file_success(monkeypatch):
    # Prepare a Parser with lines that will match def_str in the forward scan
    parser = apply_patch.Parser(current_files={}, lines=["line0", "MATCH HERE", "line2"])
    # Ensure initial state
    assert parser.index == 0

    # read_str should return the def_str that will be found in the text passed to _parse_update_file
    monkeypatch.setattr(parser, "read_str", lambda prefix: "MATCH HERE")

    # _cur_line and _norm won't be used in this test (read_str non-empty),
    # but set reasonable defaults to be safe.
    monkeypatch.setattr(parser, "_cur_line", lambda: "")
    monkeypatch.setattr(apply_patch.Parser, "_norm", staticmethod(lambda s: s))

    # Make is_done return False once (enter loop) then True to exit after one iteration
    call_states = {"calls": 0}

    def is_done(prefixes=None):
        call_states["calls"] += 1
        return call_states["calls"] >= 2

    monkeypatch.setattr(parser, "is_done", is_done)

    # Prepare peek_next_section to return a next_ctx and one chunk
    next_ctx = ["CTX_LINE"]
    chunks = [make_chunk(orig_index=5)]
    end_idx = 99
    eof = False

    def fake_peek(lines, index):
        return next_ctx, chunks, end_idx, eof

    monkeypatch.setattr(apply_patch, "peek_next_section", fake_peek)

    # find_context should locate at new_index 0 and introduce fuzz of 2
    def fake_find_context(lines_arg, next_ctx_arg, index_arg, eof_arg):
        # lines_arg is derived from the 'text' passed into _parse_update_file (splitlines),
        # so do not assert equality with parser.lines here.
        assert next_ctx_arg == next_ctx
        return 0, 2

    monkeypatch.setattr(apply_patch, "find_context", fake_find_context)

    # Run the method under test with text whose lines do not contain 'MATCH HERE'
    # but we don't require a match in the pre-scan for this test path.
    action = parser._parse_update_file("A\nB\nC")

    # Assertions: action type, fuzz updated, chunk appended and orig_index adjusted,
    # and parser.index set to end_idx
    assert action.type == apply_patch.ActionType.UPDATE
    assert parser.fuzz == 2
    assert len(action.chunks) == 1
    assert action.chunks[0].orig_index == 5  # new_index was 0, so orig_index unchanged
    assert parser.index == end_idx


def test_parse_update_file_context_not_found_raises(monkeypatch):
    # This test triggers the branch where find_context returns -1 and a DiffError is raised.

    parser = apply_patch.Parser(current_files={}, lines=["x", "y", "z"])

    # Simulate read_str returning empty and _cur_line normalized to "@@" so section_str = read_line()
    monkeypatch.setattr(parser, "read_str", lambda prefix: "")
    monkeypatch.setattr(parser, "_cur_line", lambda: "@@")
    monkeypatch.setattr(apply_patch.Parser, "_norm", staticmethod(lambda s: "@@"))
    monkeypatch.setattr(parser, "read_line", lambda: "SECTION HEADER")

    # Make is_done return False so loop enters (we expect an exception inside)
    monkeypatch.setattr(parser, "is_done", lambda prefixes=None: False)

    # Make peek_next_section return a context and set eof=True to get the 'EOF ' prefix in message
    next_ctx = ["CTX1", "CTX2"]
    chunks = []
    end_idx = 3
    eof = True

    def fake_peek(lines, index):
        return next_ctx, chunks, end_idx, eof

    monkeypatch.setattr(apply_patch, "peek_next_section", fake_peek)

    # find_context returns -1 to trigger DiffError
    def fake_find_context(lines_arg, next_ctx_arg, index_arg, eof_arg):
        assert next_ctx_arg == next_ctx
        return -1, 0

    monkeypatch.setattr(apply_patch, "find_context", fake_find_context)

    # Call and assert DiffError with expected message fragment
    with pytest.raises(apply_patch.DiffError) as excinfo:
        parser._parse_update_file("one\ntwo\nthree")

    msg = str(excinfo.value)
    # Should mention 'Invalid EOF context' (because eof True) and include the context text
    assert "Invalid EOF context" in msg or "Invalid EOF " in msg
    for line in next_ctx:
        assert line in msg
