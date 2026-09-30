import pytest

from aider.coders import udiff_coder


def test_returns_none_when_before_empty_round_107(monkeypatch):
    """If hunk_to_before_after returns an empty `before`, directly_apply_hunk should return None
    and should not call the lines=True variant or flexi_just_search_and_replace."""
    calls = []

    def fake_hunk_to_before_after(hunk, lines=False):
        calls.append((hunk, lines))
        if lines:
            # Should not be reached in this case
            return ([], None)
        return ("", "after")

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", fake_hunk_to_before_after)

    # Replace flexi_just_search_and_replace with a callable that would fail if called
    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", lambda texts: (_ for _ in ()).throw(RuntimeError("should not be called")))

    result = udiff_coder.directly_apply_hunk("some content", "dummy_hunk")

    assert result is None
    # Only the initial hunk_to_before_after call (lines=False) should have occurred
    assert len(calls) == 1
    assert calls[0][1] is False


def test_refuse_repeated_search_replace_small_context_round_107(monkeypatch):
    """When the stripped before_lines are shorter than 10 and `before` appears multiple times
    in content, the function should refuse and return None without calling the replacer."""

    def fake_hunk_to_before_after(hunk, lines=False):
        if lines:
            # This produces a tiny before_lines when joined (single non-whitespace char)
            return (["  x\n"], None)
        return ("x", "y")

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", fake_hunk_to_before_after)

    called = []

    def fake_flexi(texts):
        called.append(True)
        return "SHOULD_NOT_BE_RETURNED"

    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", fake_flexi)

    # content contains the `before` twice -> content.count(before) > 1
    content = "prefix x middle x suffix"
    result = udiff_coder.directly_apply_hunk(content, "hunk")

    assert result is None
    # flexi_just_search_and_replace must not have been invoked
    assert called == []


def test_flexi_replace_success_round_107(monkeypatch):
    """When context is large enough (joined before_lines length >= 10) and there's no
    repeated tiny context, flexi_just_search_and_replace should be invoked and its
    return value should be returned by directly_apply_hunk."""

    def fake_hunk_to_before_after(hunk, lines=False):
        if lines:
            # Produces a joined stripped length of exactly 10 characters -> bypass the tiny-context guard
            return (["aaaaa\n", "bbbbb\n"], None)
        return ("needle", "replacement")

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", fake_hunk_to_before_after)

    captured = {}

    def fake_flexi(texts):
        # capture the argument shape and return a predictable new content
        captured['texts'] = texts
        return "NEW_CONTENT"

    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", fake_flexi)

    content = "start needle end"
    result = udiff_coder.directly_apply_hunk(content, "hunk")

    assert result == "NEW_CONTENT"
    # ensure the replacer was called with [before, after, content]
    assert captured['texts'] == ["needle", "replacement", content]


def test_flexi_replace_search_text_not_unique_round_107(monkeypatch):
    """If flexi_just_search_and_replace raises SearchTextNotUnique, directly_apply_hunk
    should catch it and return None."""

    def fake_hunk_to_before_after(hunk, lines=False):
        if lines:
            # long enough to bypass the tiny-context early return
            return (["xxxxxxxxxx\n"], None)
        return ("a", "b")

    monkeypatch.setattr(udiff_coder, "hunk_to_before_after", fake_hunk_to_before_after)

    class DummyNotUnique(Exception):
        pass

    # Patch the exception symbol used by the module so the except catches our raised type
    monkeypatch.setattr(udiff_coder, "SearchTextNotUnique", DummyNotUnique)

    def raising_flexi(texts):
        raise DummyNotUnique("not unique")

    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", raising_flexi)

    result = udiff_coder.directly_apply_hunk("contains a", "hunk")

    assert result is None
