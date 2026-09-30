import pytest

from aider.coders.search_replace import RelativeIndenter

ARROW = "\u2190"


def test_marker_uses_arrow_when_missing_round_155():
    # When none of the input texts contain the ARROW character,
    # __init__ should set marker to the ARROW constant.
    texts = ["hello", "world", "no arrow here"]
    ri = RelativeIndenter(texts)
    assert ri.marker == ARROW


def test_marker_uses_select_unique_when_arrow_present_round_155(monkeypatch):
    # When at least one input text contains ARROW, __init__ should call
    # select_unique_marker and use its return value as marker.
    texts = [f"contains {ARROW} here", "other text"]

    captured = {}

    def fake_select_unique_marker(self, chars):
        # capture the argument passed in for later inspection
        captured['chars'] = set(chars)
        return 'UNIQUE_MARKER_Z'

    # Patch the method on the class where __init__ will resolve it.
    monkeypatch.setattr(RelativeIndenter, 'select_unique_marker', fake_select_unique_marker)

    ri = RelativeIndenter(texts)

    # The marker should be whatever our fake method returned.
    assert ri.marker == 'UNIQUE_MARKER_Z'

    # And the captured chars provided to select_unique_marker must include ARROW
    assert ARROW in captured['chars']
