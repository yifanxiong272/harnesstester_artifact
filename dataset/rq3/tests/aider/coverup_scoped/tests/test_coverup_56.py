# file: aider/coders/patch_coder.py:81-93
# asked: {"lines": [83, 85, 86, 87, 88, 90, 91, 93], "branches": [[83, 85], [83, 93], [85, 86], [85, 90], [87, 88], [87, 90]]}
# gained: {"lines": [83, 85, 86, 87, 88, 90, 91, 93], "branches": [[83, 85], [83, 93], [85, 86], [85, 90], [87, 88], [87, 90]]}

import pytest
from types import SimpleNamespace

from aider.coders import patch_coder as pc


def test_find_context_eof_matches_end(monkeypatch):
    lines = ["line1", "line2", "line3", "line4"]
    context = ["line3", "line4"]
    start = 0

    # Ensure the core is called only for the end position and returns a match
    def fake_find_context_core(lines_arg, context_arg, start_arg):
        assert lines_arg is lines
        assert context_arg is context
        # Expect to be called with start == len(lines) - len(context)
        assert start_arg == len(lines) - len(context)
        return (start_arg, 5)

    monkeypatch.setattr(pc, "find_context_core", fake_find_context_core)

    idx, fuzz = pc.find_context(lines, context, start, eof=True)
    assert idx == len(lines) - len(context)
    assert fuzz == 5


def test_find_context_eof_not_found_at_end_fallback(monkeypatch):
    lines = ["a", "b", "c", "d"]
    context = ["c", "d"]
    start = 0
    end_start = len(lines) - len(context)

    # First call (at end) returns -1 to force fallback; second call (from start) returns a real match
    def fake_find_context_core(lines_arg, context_arg, start_arg):
        assert lines_arg is lines
        assert context_arg is context
        if start_arg == end_start:
            return (-1, 0)
        elif start_arg == start:
            return (1, 3)
        else:
            raise AssertionError("Unexpected start_arg: %r" % (start_arg,))

    monkeypatch.setattr(pc, "find_context_core", fake_find_context_core)

    idx, fuzz = pc.find_context(lines, context, start, eof=True)
    assert idx == 1
    # fuzz should have the added EOF penalty of 10000
    assert fuzz == 3 + 10000


def test_find_context_non_eof_uses_start(monkeypatch):
    lines = ["x", "y", "z"]
    context = ["y"]
    start = 2

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        assert lines_arg is lines
        assert context_arg is context
        # Should be called with the provided start when eof is False
        assert start_arg == start
        return (-2, 42)

    monkeypatch.setattr(pc, "find_context_core", fake_find_context_core)

    idx, fuzz = pc.find_context(lines, context, start, eof=False)
    assert idx == -2
    assert fuzz == 42


def test_find_context_eof_lines_short_skips_end_try(monkeypatch):
    # lines shorter than context: should skip the "at end" attempt and directly call start once
    lines = ["only"]
    context = ["longer", "context"]
    start = 0

    def fake_find_context_core(lines_arg, context_arg, start_arg):
        assert lines_arg is lines
        assert context_arg is context
        # Only called with the provided start
        assert start_arg == start
        return (4, 6)

    monkeypatch.setattr(pc, "find_context_core", fake_find_context_core)

    idx, fuzz = pc.find_context(lines, context, start, eof=True)
    assert idx == 4
    assert fuzz == 6 + 10000
