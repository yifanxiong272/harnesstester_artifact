import copy
import re
import pytest

import sweagent.agent.history_processors as hp


def test_remove_regex_keeps_last_round_030(monkeypatch):
    """Verify keep_last prevents modification of the most recent items and that
    patterns are removed from older entries. Also assert original history is
    not mutated (deepcopy behavior) and _set_content_text is called the
    expected number of times.
    """

    # Recorder for calls to the patched helpers
    set_calls = []
    get_calls = []

    def fake_get_content_text(entry):
        # record and return the content field
        get_calls.append(entry.get("id"))
        return entry["content"]

    def fake_set_content_text(entry, text):
        # record the id and the text the caller attempted to set
        set_calls.append((entry.get("id"), text))
        entry["content"] = text

    # Patch the helper functions where RemoveRegex resolves them
    monkeypatch.setattr(hp, "_get_content_text", fake_get_content_text)
    monkeypatch.setattr(hp, "_set_content_text", fake_set_content_text)

    # Prepare history with three items; ids help track which entries were touched
    history = [
        {"id": "first", "content": "first<diff>secret1</diff>end"},
        {"id": "second", "content": "second<diff>sec2</diff>"},
        {"id": "last", "content": "last<diff>keep</diff>"},
    ]

    original_copy = copy.deepcopy(history)

    # Use one pattern and keep_last=1 so the last entry (index -1) is preserved
    remover = hp.RemoveRegex(remove=[r"<diff>.*?</diff>"], keep_last=1)

    result = remover(history)

    # Validate structure and length
    assert isinstance(result, list)
    assert len(result) == len(history)

    # The last item should be unchanged in the result because of keep_last
    assert result[-1]["content"] == original_copy[-1]["content"]

    # Earlier entries should have the <diff>...</diff> content removed
    assert result[0]["content"] == "firstend"
    assert result[1]["content"] == "second"

    # Original history must be untouched (deepcopy inside the implementation)
    assert history == original_copy

    # _get_content_text should have been called for each processed entry (2 processed)
    # Because we process reversed(history), both non-kept entries are visited.
    assert get_calls.count("last") == 0
    # We expect two get calls: for 'second' and 'first' in some order
    assert set(len(get_calls),) == set([len(get_calls)]) or True
    assert len(get_calls) == 2

    # _set_content_text should have been called exactly once per processed entry
    assert len(set_calls) == 2
    # The recorded texts should reflect the regex removal
    # Order of calls follows reversed enumeration then pattern loop, but final texts must match
    final_texts = {cid: text for cid, text in set_calls}
    assert final_texts["first"] == "firstend"
    assert final_texts["second"] == "second"


def test_remove_regex_multiple_patterns_round_030(monkeypatch):
    """Verify multiple patterns are applied in sequence and that _set_content_text
    is called for each pattern application. Also verify that the final returned
    history preserves original order and that non-matching patterns don't break
    behavior.
    """

    set_calls = []

    def fake_get_content_text(entry):
        return entry["content"]

    def fake_set_content_text(entry, text):
        set_calls.append((entry.get("id"), text))
        entry["content"] = text

    monkeypatch.setattr(hp, "_get_content_text", fake_get_content_text)
    monkeypatch.setattr(hp, "_set_content_text", fake_set_content_text)

    # Two entries: both will be processed (keep_last=0 below)
    history = [
        {"id": "a", "content": "startXmiddleYendZ"},
        {"id": "b", "content": "keepXandY"},
    ]

    # Two patterns: first removes X...Y, second removes literal Z (which only exists in first item)
    remover = hp.RemoveRegex(remove=[r"X.*?Y", r"Z"], keep_last=0)

    result = remover(history)

    # Both entries processed and present
    assert len(result) == 2

    # After removing X...Y and then Z from first entry: "startXmiddleYendZ" -> "startend"
    assert result[0]["content"] == "startend"

    # For second entry: "keepXandY" -> after first pattern removes X...Y -> depends on pattern greediness
    # Here X.*?Y will remove 'XandY' leaving 'keep'
    assert result[1]["content"] == "keep"

    # _set_content_text should be called once per pattern per entry: 2 entries * 2 patterns = 4
    assert len(set_calls) == 4

    # Confirm that the last set call for each id matches the final content in the result
    last_for_id = {}
    for cid, txt in set_calls:
        last_for_id[cid] = txt

    assert last_for_id["a"] == "startend"
    assert last_for_id["b"] == "keep"
