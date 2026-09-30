# file: aider/coders/udiff_coder.py:209-240
# asked: {"lines": [210, 212, 214, 215, 216, 217, 221, 223, 224, 225, 227, 228, 230, 231, 232, 234, 235, 237, 238, 240], "branches": [[215, 216], [215, 223], [216, 217], [216, 221], [224, 225], [224, 227], [227, 228], [227, 230], [234, 235], [234, 237]]}
# gained: {"lines": [210, 212, 214, 215, 216, 217, 221, 223, 224, 225, 227, 228, 230, 231, 232, 234, 237, 238, 240], "branches": [[215, 216], [215, 223], [216, 217], [216, 221], [224, 225], [224, 227], [227, 228], [227, 230], [234, 237]]}

import importlib
import pytest

mod = importlib.import_module("aider.coders.udiff_coder")


def test_returns_original_hunk_when_new_before_empty(monkeypatch):
    # Arrange: prepare stubs to drive the branch where directly_apply_hunk returns falsy
    original_hunk = ["@@ -1,1 +1,1 @@\n", "-old\n", "+new\n"]

    def fake_hunk_to_before_after(hunk):
        assert hunk is original_hunk
        return "before\n", "after\n"

    def fake_diff_lines(before, content):
        # include a '+' line that should be ignored, and a '-' line preserved
        return ["+added\n", "-removed\n"]

    def fake_directly_apply_hunk(before, back_diff):
        # simulate failure to apply -> return empty string -> triggers early return
        assert back_diff == ["-removed\n"]
        return ""

    monkeypatch.setattr(mod, "hunk_to_before_after", fake_hunk_to_before_after)
    monkeypatch.setattr(mod, "diff_lines", fake_diff_lines)
    monkeypatch.setattr(mod, "directly_apply_hunk", fake_directly_apply_hunk)

    # Act
    result = mod.make_new_lines_explicit("some content", original_hunk)

    # Assert: should return the original hunk unchanged
    assert result is original_hunk


def test_returns_original_hunk_when_new_before_too_short(monkeypatch):
    # Arrange: directly_apply_hunk returns a string whose stripped length < 10
    original_hunk = ["@@ dummy\n"]

    def fake_hunk_to_before_after(hunk):
        return "before content that is long enough\n", "after content\n"

    def fake_diff_lines(before, content):
        return ["-something\n"]

    def fake_directly_apply_hunk(before, back_diff):
        # Return a very short result (after stripping < 10 chars)
        return " short\n"

    monkeypatch.setattr(mod, "hunk_to_before_after", fake_hunk_to_before_after)
    monkeypatch.setattr(mod, "diff_lines", fake_diff_lines)
    monkeypatch.setattr(mod, "directly_apply_hunk", fake_directly_apply_hunk)

    # Act
    result = mod.make_new_lines_explicit("irrelevant", original_hunk)

    # Assert: still returns original hunk due to new_before.strip() being too short
    assert result is original_hunk


def test_returns_converted_new_hunk_when_conditions_met(monkeypatch):
    # Arrange: create before and after where new_before is slightly shorter but >= 66%
    before = "line1\nline2\nline3\nline4\nline5\nline6\n"
    # new_before will drop line6
    new_before = "line1\nline2\nline3\nline4\nline5\n"
    after = before  # after contains the original 6 lines

    original_hunk = ["@@ original\n"]

    def fake_hunk_to_before_after(hunk):
        assert hunk is original_hunk
        return before, after

    def fake_diff_lines(before_arg, content):
        # back_diff should keep '-' lines; '+' lines would be skipped by the function
        return ["-line6\n"]

    def fake_directly_apply_hunk(before_arg, back_diff):
        assert back_diff == ["-line6\n"]
        return new_before

    monkeypatch.setattr(mod, "hunk_to_before_after", fake_hunk_to_before_after)
    monkeypatch.setattr(mod, "diff_lines", fake_diff_lines)
    monkeypatch.setattr(mod, "directly_apply_hunk", fake_directly_apply_hunk)

    # Act
    result = mod.make_new_lines_explicit("unused content", original_hunk)

    # Assert: should return a new hunk list (unified diff lines, headers stripped)
    assert isinstance(result, list)
    # The unified diff between new_before (5 lines) and after (6 lines) should include the added sixth line
    # after headers are removed. Look for a line that adds line6.
    assert any(line.startswith("+line6") or line.startswith("+line6\n") for line in result)
    # And ensure we did not simply return the original hunk object
    assert result is not original_hunk
