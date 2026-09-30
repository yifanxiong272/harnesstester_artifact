# file: aider/coders/search_replace.py:83-96
# asked: {"lines": [88, 89, 90, 92, 93, 94, 96], "branches": [[89, 90], [89, 92], [93, 94], [93, 96]]}
# gained: {"lines": [88, 89, 90, 92, 93, 94, 96], "branches": [[89, 90], [89, 92], [93, 94], [93, 96]]}

import pytest
from aider.coders import search_replace


def test_relative_indenter_sets_arrow_when_missing(monkeypatch):
    RelativeIndenter = search_replace.RelativeIndenter

    # Ensure select_unique_marker is not called in this case.
    def _fail_if_called(self, chars):
        raise AssertionError("select_unique_marker should not be called when ARROW is not in texts")

    monkeypatch.setattr(RelativeIndenter, "select_unique_marker", _fail_if_called)

    indenter = RelativeIndenter(["hello", "world", "no arrow here"])
    assert indenter.marker == "←"


def test_relative_indenter_uses_select_unique_marker_when_arrow_present(monkeypatch):
    RelativeIndenter = search_replace.RelativeIndenter

    called = {"called": False}

    def fake_select_unique_marker(self, chars):
        # Assert that the ARROW is indeed present in the computed chars set
        assert "←" in chars
        # Also assert that other chars from inputs are present
        assert "a" in chars or "h" in chars
        called["called"] = True
        return "#"

    monkeypatch.setattr(RelativeIndenter, "select_unique_marker", fake_select_unique_marker)

    # Provide texts that include the ARROW so the branch uses select_unique_marker
    texts_with_arrow = ["contains ← here", "and some other text"]
    indenter = RelativeIndenter(texts_with_arrow)

    assert called["called"] is True
    assert indenter.marker == "#"
