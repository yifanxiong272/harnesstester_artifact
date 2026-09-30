# file: aider/coders/udiff_coder.py:209-240
# asked: {"lines": [210, 212, 214, 215, 216, 217, 221, 223, 224, 225, 227, 228, 230, 231, 232, 234, 235, 237, 238, 240], "branches": [[215, 216], [215, 223], [216, 217], [216, 221], [224, 225], [224, 227], [227, 228], [227, 230], [234, 235], [234, 237]]}
# gained: {"lines": [210, 212, 214, 215, 216, 217, 221, 223, 224, 225, 227, 228, 230, 231, 232, 234, 235, 237, 238, 240], "branches": [[215, 216], [215, 223], [216, 217], [216, 221], [224, 225], [224, 227], [227, 228], [227, 230], [234, 235], [234, 237]]}

import difflib
import pytest

import aider.coders.udiff_coder as udiff


def test_returns_hunk_when_direct_apply_returns_none(monkeypatch):
    before = "line1\nline2\nline3\n"
    after = "line1\nline2\nline3\n"
    original_hunk = ["@@ -1,3 +1,3 @@\n", " line1\n", " line2\n", " line3\n"]

    # hunk_to_before_after should be called and return our before/after
    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: (before, after))

    # diff_lines returns a mix; plus lines should be skipped when building back_diff
    monkeypatch.setattr(udiff, "diff_lines", lambda b, c: ["+added\n", "-removed\n", " unchanged\n"])

    # directly_apply_hunk returns a falsy value -> make_new_lines_explicit should return original hunk
    monkeypatch.setattr(udiff, "directly_apply_hunk", lambda b, back_diff: None)

    result = udiff.make_new_lines_explicit("some content", original_hunk)
    assert result is original_hunk


def test_returns_hunk_when_new_before_too_short(monkeypatch):
    before = "aaaaaaaaaaaaaaa\nbbbbbbbbbbbbbbb\n"  # fairly long before (2 lines)
    after = "aaaaaaaaaaaaaaa\nbbbbbbbbbbbbbbb\n"
    original_hunk = ["orig"]

    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: (before, after))
    monkeypatch.setattr(udiff, "diff_lines", lambda b, c: ["-x\n", " y\n"])
    # new_before is short when stripped (< 10) -> should return original hunk
    monkeypatch.setattr(udiff, "directly_apply_hunk", lambda b, back_diff: " tiny\n")

    result = udiff.make_new_lines_explicit("content", original_hunk)
    assert result is original_hunk


def test_returns_hunk_when_new_before_too_small_relative_to_before(monkeypatch):
    # make before many lines so that new_before has fewer than 66% of lines
    before = "A\n" * 100  # 100 lines
    after = "A\n" * 100
    original_hunk = ["orig-hunk"]

    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: (before, after))
    monkeypatch.setattr(udiff, "diff_lines", lambda b, c: ["-old\n", " unchanged\n"])
    # new_before has 60 lines -> 60 < 100 * 0.66 -> should return original_hunk
    monkeypatch.setattr(udiff, "directly_apply_hunk", lambda b, back_diff: "B\n" * 60)

    result = udiff.make_new_lines_explicit("content", original_hunk)
    assert result is original_hunk


def test_returns_new_hunk_on_success(monkeypatch):
    # before and after that will generate a unified diff when new_before differs from after
    before = "line1\nline2\nline3\n"
    # after differs from new_before to create diff
    after = "line1\nline2 after\nline3\n"
    original_hunk = ["@@ -1,3 +1,3 @@\n", " line1\n", " line2\n", " line3\n"]

    # Provide hunk_to_before_after
    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: (before, after))

    # Provide diff_lines containing some '+' entries which should be skipped when forming back_diff
    monkeypatch.setattr(udiff, "diff_lines", lambda b, c: ["+should_skip\n", "-keep-this\n", " unchanged\n"])

    # Define directly_apply_hunk to assert it receives back_diff without '+' lines and return a valid new_before
    def fake_directly_apply_hunk(b, back_diff):
        # back_diff should not contain lines starting with '+'
        assert all(not (line and line[0] == "+") for line in back_diff)
        # Return a new_before string that is:
        # - not falsy
        # - strip length >= 10
        # - at least 66% of original before length in lines
        new_before = "line1\nline2 modified\nline3\n"
        assert len(new_before.strip()) >= 10
        assert len(new_before.splitlines(keepends=True)) >= len(b.splitlines(keepends=True)) * 0.66
        return new_before

    monkeypatch.setattr(udiff, "directly_apply_hunk", fake_directly_apply_hunk)

    result = udiff.make_new_lines_explicit("some content", original_hunk)

    # Should have produced a new hunk list (not the original_hunk)
    assert isinstance(result, list)
    assert result is not original_hunk
    # The unified diff (after slicing off first 3 header lines) should contain diff markers
    assert any((line and line[0] in "+-") for line in result)
