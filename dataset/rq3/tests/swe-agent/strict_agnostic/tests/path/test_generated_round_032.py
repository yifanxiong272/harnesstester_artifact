import copy
import re
import importlib
import pytest

# Import the module under test
import sweagent.agent.history_processors as hp

# The tests monkeypatch internal helper functions _get_content_text and _set_content_text
# so that we can exercise RemoveRegex behavior deterministically on simple dict-based
# history items without depending on other project types or implementations.


def test_keep_last_preserves_entry_round_032(monkeypatch):
    """
    - Ensure that keep_last causes the last N history items (from the end) to be left
      unchanged by the processor (branch i_entry < self.keep_last).
    - Ensure other entries have the remove regex applied.
    """
    # Simple helper implementations that operate on a dict with a 'text' key.
    monkeypatch.setattr(hp, '_get_content_text', lambda entry: entry['text'])
    monkeypatch.setattr(hp, '_set_content_text', lambda entry, text: entry.__setitem__('text', text))

    # Create a history with two items. The second element is the most recent.
    original_history = [
        {'text': 'first <diff>SECRET1</diff> end'},
        {'text': 'last <diff>SECRET2</diff> end'},
    ]

    # Make a deep copy to assert the original is not mutated by the processor
    before = copy.deepcopy(original_history)

    # Instantiate RemoveRegex to keep the last 1 item unchanged
    proc = hp.RemoveRegex(keep_last=1)

    processed = proc(original_history)

    # The processor returns a new list; verify original preserved
    assert original_history == before

    # The last item (index 1) should be preserved (kept unchanged)
    assert processed[1]['text'] == 'last <diff>SECRET2</diff> end'

    # The first item should have the <diff>...</diff> content removed
    # Default pattern is '<diff>.*</diff>' with DOTALL, so the tag and its contents are removed
    assert processed[0]['text'] == 'first  end'


def test_multiple_patterns_and_empty_history_round_032(monkeypatch):
    """
    - Ensure multiple patterns in `remove` are applied in order (inner loop over patterns).
    - Ensure _set_content_text is called for each pattern application.
    - Also verify that an empty history returns an empty list (loop not entered).
    """
    # Counters to observe calls to the helper functions
    set_calls = []

    def fake_get(entry):
        return entry['text']

    def fake_set(entry, text):
        # Record that _set_content_text was called and what the text became
        set_calls.append(text)
        entry['text'] = text

    monkeypatch.setattr(hp, '_get_content_text', fake_get)
    monkeypatch.setattr(hp, '_set_content_text', fake_set)

    # Case 1: empty history -> should return empty list
    proc_empty = hp.RemoveRegex(keep_last=0, remove=[r"foo"])  # remove list irrelevant here
    assert proc_empty([]) == []

    # Case 2: history with one item and two remove patterns
    entry = {'text': 'foo middle BAR baz'}
    history = [entry]

    # Patterns: remove 'foo' (case-sensitive), then remove 'BAR' (uppercase)
    proc = hp.RemoveRegex(keep_last=0, remove=[r'foo', r'BAR'])

    processed = proc(history)

    # Two patterns should have been applied sequentially; set_calls should have two recorded states
    assert len(set_calls) == 2

    # After removing 'foo' and 'BAR', remaining text should be ' middle  baz'
    # (note space handling: re.sub removes matched sequences but leaves surrounding spaces)
    assert processed[0]['text'] == ' middle  baz'

    # Ensure original entry was not mutated (deepcopy inside the processor)
    assert history[0]['text'] == 'foo middle BAR baz'
