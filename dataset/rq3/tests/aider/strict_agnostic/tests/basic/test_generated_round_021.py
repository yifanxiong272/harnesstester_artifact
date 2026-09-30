import pytest
from types import SimpleNamespace

from aider.io import AutoCompleter, CommandCompletionException
from prompt_toolkit.completion import Completion


class DummyDocument:
    def __init__(self, text):
        self.text_before_cursor = text


def make_ac_instance():
    # Create an AutoCompleter without running its real __init__ (avoid heavy setup)
    ac = object.__new__(AutoCompleter)
    # noop tokenize to avoid altering state
    ac.tokenize = lambda: None
    # basic structures used by get_completions
    ac.words = set()
    ac.fname_to_rel_fnames = {}
    return ac


def _display_text_from_completion(comp: Completion) -> str:
    """Return a plain text string for the Completion.display which may be
    a FormattedText or a simple string. This makes assertions deterministic.
    """
    disp = getattr(comp, "display", None)
    if disp is None:
        return ""
    # If it's a simple string
    if isinstance(disp, str):
        return disp
    # If it's a sequence of (style, text) pieces (FormattedText), join the text parts
    try:
        return "".join(part[1] for part in disp)
    except Exception:
        # Fallback to str()
        return str(disp)


def test_get_completions_empty_round_021():
    """
    When the document has no words, get_completions should yield nothing (early return path).
    Covers lines around the `if not words: return` branch.
    """
    ac = make_ac_instance()
    doc = DummyDocument("")

    results = list(ac.get_completions(doc, None))
    assert results == [], "Expected no completions for empty input"


def test_get_completions_trailing_space_round_021():
    """
    When the cursor is after a space, get_completions should not continue completing.
    Covers the `if text and text[-1].isspace(): return` branch.
    """
    ac = make_ac_instance()
    doc = DummyDocument("hello ")

    results = list(ac.get_completions(doc, None))
    assert results == [], "Expected no completions when text ends with a space"


def test_get_completions_command_yield_round_021():
    """
    If text starts with '/', get_completions should yield completions from
    get_command_completions and then return early (no fallback to normal completions).
    This exercises the 'yield from self.get_command_completions(...); return' path.
    """
    ac = make_ac_instance()

    # Provide a command completion generator that yields a single Completion
    def command_completions(document, complete_event, text, words):
        yield Completion("/cmd-insert", start_position=-len(words[-1]), display="/cmd")

    ac.get_command_completions = command_completions

    doc = DummyDocument("/cmd")
    results = list(ac.get_completions(doc, None))

    assert len(results) == 1
    comp = results[0]
    assert isinstance(comp, Completion)
    assert comp.text == "/cmd-insert"
    assert comp.start_position == -len("/cmd")
    # Use helper to extract plain display text for deterministic assertion
    assert _display_text_from_completion(comp) == "/cmd"


def test_get_completions_command_exception_fallback_round_021():
    """
    If get_command_completions raises CommandCompletionException, get_completions should
    fall through to normal completion generation. This exercises the except: pass path.
    """
    ac = make_ac_instance()

    def raising_command_completions(document, complete_event, text, words):
        raise CommandCompletionException("no command completion")

    ac.get_command_completions = raising_command_completions

    # Prepare normal completion candidates so fallback produces results
    # Use a word that matches the typed last_word (case preserved)
    ac.words = {"/fallback", "Other"}
    # also provide a rel filename mapping to exercise rel_fnames branch
    ac.fname_to_rel_fnames = {"/fallback": ["rel_file.txt"]}

    doc = DummyDocument("/fallback")
    results = list(ac.get_completions(doc, None))

    # Expect at least two completions: the word itself and its rel file
    assert any(isinstance(r, Completion) for r in results)
    displays = {_display_text_from_completion(r) for r in results}
    texts = [r.text for r in results]
    assert "/fallback" in displays or "rel_file.txt" in texts
    for r in results:
        # ensure returned start_position is negative length of last word
        assert r.start_position == -len("/fallback")


def test_get_completions_normal_matching_and_relfiles_round_021():
    """
    Test normal matching behavior (case-insensitive startswith) and that rel_fnames
    entries produce extra completions. Also ensures the minimum-length check
    (len(last_word) >= 3) is respected by using a 3-char last word.
    """
    ac = make_ac_instance()

    # Provide candidate words as both plain strings and tuples
    ac.words = {"Love", ("lovely", "lovely-insert")}
    # Map a rel filename for the 'Love' match
    ac.fname_to_rel_fnames = {"Love": ["love_notes.md"]}

    doc = DummyDocument("I lov")  # last_word == 'lov' (3 chars)
    results = list(ac.get_completions(doc, None))

    # Collect displays and texts for easier assertions
    texts = [r.text for r in results]
    displays = [_display_text_from_completion(r) for r in results]

    # Expect at least the 'Love' completion (case-insensitive) and the rel filename
    assert any(d.lower() == "love" for d in displays), f"Expected 'Love' in displays, got {displays}"
    assert any(t == "love_notes.md" for t in texts), f"Expected rel filename in texts, got {texts}"

    # All returned completions should have start_position == -len(last_word)
    assert all(r.start_position == -3 for r in results)
