import importlib
import difflib
import pytest

udiff_coder = importlib.import_module("aider.coders.udiff_coder")


def test_make_new_lines_explicit_returns_hunk_when_directly_apply_returns_falsy_round_049(monkeypatch):
    # Arrange: prepare a sentinel hunk object and stub collaborators
    sentinel_hunk = ['@@ -1,2 +1,2 @@']
    before = "one\ntwo\n"
    after = "one\ntwo\n"

    monkeypatch.setattr(udiff_coder, 'hunk_to_before_after', lambda h: (before, after))
    monkeypatch.setattr(udiff_coder, 'diff_lines', lambda b, c: ['+added', '-removed', ' unchanged'])
    # directly_apply_hunk returns falsy -> should return original hunk
    monkeypatch.setattr(udiff_coder, 'directly_apply_hunk', lambda b, bd: '')

    # Act
    result = udiff_coder.make_new_lines_explicit('content not used', sentinel_hunk)

    # Assert
    assert result is sentinel_hunk


def test_make_new_lines_explicit_returns_hunk_when_new_before_too_short_round_049(monkeypatch):
    sentinel_hunk = ['@@ -1,1 +1,1 @@']
    before = "some before content that is irrelevant\n"
    after = "some after content\n"

    monkeypatch.setattr(udiff_coder, 'hunk_to_before_after', lambda h: (before, after))
    monkeypatch.setattr(udiff_coder, 'diff_lines', lambda b, c: ['-x'])
    # new_before too short (strip length < 10) -> return hunk
    monkeypatch.setattr(udiff_coder, 'directly_apply_hunk', lambda b, bd: 'short')

    result = udiff_coder.make_new_lines_explicit('irrelevant', sentinel_hunk)

    assert result is sentinel_hunk


def test_make_new_lines_explicit_returns_hunk_when_new_before_under_fraction_threshold_round_049(monkeypatch):
    # Arrange: set before long, new_before shorter than 66% but >= 10 chars
    sentinel_hunk = ['@@ -1,100 +1,60 @@']
    before = 'A' * 100  # length 100
    after = 'after content\n'

    monkeypatch.setattr(udiff_coder, 'hunk_to_before_after', lambda h: (before, after))
    # diff_lines content doesn't matter for behavior here
    monkeypatch.setattr(udiff_coder, 'diff_lines', lambda b, c: ['-line'])
    # new_before length 60 -> 60 < 66 -> should return hunk; ensure strip() >= 10
    monkeypatch.setattr(udiff_coder, 'directly_apply_hunk', lambda b, bd: 'X' * 60)

    result = udiff_coder.make_new_lines_explicit('irrelevant', sentinel_hunk)

    assert result is sentinel_hunk


def test_make_new_lines_explicit_produces_unified_diff_list_and_passes_back_diff_round_049(monkeypatch):
    # Successful path: directly_apply_hunk returns a new_before that is >= 66% of before
    sentinel_hunk = ['@@ -1,3 +1,3 @@']
    before = 'line1\nline2\nline3\n'
    after = 'line1\nline2 changed\nline3\n'

    monkeypatch.setattr(udiff_coder, 'hunk_to_before_after', lambda h: (before, after))

    # Provide a diff that contains lines starting with '+' and '-' and ' '.
    # The function should skip '+' lines when building back_diff.
    monkeypatch.setattr(udiff_coder, 'diff_lines', lambda b, c: ['+added_line\n', '-removed_line\n', ' unchanged\n'])

    captured = {}

    def fake_directly_apply_hunk(b, back_diff):
        # Capture the back_diff passed in for later assertions
        captured['back_diff'] = list(back_diff)
        # Return a new_before that is the same number of lines as before (so passes the 0.66 check)
        return before

    monkeypatch.setattr(udiff_coder, 'directly_apply_hunk', fake_directly_apply_hunk)

    result = udiff_coder.make_new_lines_explicit('content', sentinel_hunk)

    # Assert that the back_diff passed to directly_apply_hunk had '+'-prefixed lines removed
    assert captured['back_diff'] == ['-removed_line\n', ' unchanged\n']

    # Result should be a list (the unified diff lines after stripping the header triple)
    assert isinstance(result, list)
    # unified_diff output (after slicing) should contain diff markers like + or - for changed lines
    assert any(line.startswith('+') or line.startswith('-') for line in result), "expected diff content lines"
