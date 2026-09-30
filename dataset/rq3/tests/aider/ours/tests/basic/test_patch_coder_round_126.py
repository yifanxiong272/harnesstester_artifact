import pytest
from aider.coders import patch_coder


def test_find_context_eof_found_at_end_round_126(monkeypatch):
    # Case: eof True, lines long enough so end-search is attempted and succeeds.
    lines = ["a", "b", "c", "d"]
    context = ["c", "d"]
    start = 0

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        # Should be called with the index pointing to the very end
        assert lines_arg is lines
        assert context_arg is context
        assert start_arg == len(lines) - len(context)
        return (5, 2)

    monkeypatch.setattr(patch_coder, "find_context_core", fake_find_context_core)

    result = patch_coder.find_context(lines, context, start, eof=True)
    assert result == (5, 2)


def test_find_context_eof_end_not_found_fallback_found_round_126(monkeypatch):
    # Case: eof True, end attempt returns -1; fallback from `start` returns a match.
    lines = ["a", "b", "c"]
    context = ["b", "c"]
    start = 1

    calls = []

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        # record the start_arg to assert first attempted end index then fallback start
        calls.append(start_arg)
        if start_arg == len(lines) - len(context):
            return (-1, 0)
        if start_arg == start:
            return (3, 4)
        raise AssertionError("Unexpected start_arg: {}".format(start_arg))

    monkeypatch.setattr(patch_coder, "find_context_core", fake_find_context_core)

    result = patch_coder.find_context(lines, context, start, eof=True)
    # Since the end attempt returned -1, the fallback fuzz gets +10_000
    assert result == (3, 10004)
    # Ensure both locations were attempted in order
    assert calls == [len(lines) - len(context), start]


def test_find_context_eof_lines_shorter_than_context_round_126(monkeypatch):
    # Case: eof True but lines shorter than context -> skip end attempt, only fallback used
    lines = ["only_line"]
    context = ["x", "y"]  # longer than lines
    start = 0

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        # Only fallback (start) should be called
        assert start_arg == start
        return (2, 7)

    monkeypatch.setattr(patch_coder, "find_context_core", fake_find_context_core)

    result = patch_coder.find_context(lines, context, start, eof=True)
    assert result == (2, 10007)


def test_find_context_non_eof_uses_start_directly_round_126(monkeypatch):
    # Case: eof False -> directly delegate to find_context_core with start
    lines = ["1", "2"]
    context = ["2"]
    start = 0

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        assert start_arg == start
        return (0, 1)

    monkeypatch.setattr(patch_coder, "find_context_core", fake_find_context_core)

    result = patch_coder.find_context(lines, context, start, eof=False)
    assert result == (0, 1)
