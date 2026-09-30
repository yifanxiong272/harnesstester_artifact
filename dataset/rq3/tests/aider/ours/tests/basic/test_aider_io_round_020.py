import types

import pytest

import aider.io as io_module
from aider.io import AutoCompleter, CommandCompletionException


class DummyDoc:
    def __init__(self, text):
        # attribute expected by get_completions
        self.text_before_cursor = text


class DummyCompletion:
    def __init__(self, text, start_position=0, display=None):
        self.text = text
        self.start_position = start_position
        self.display = display

    def __repr__(self):
        return f"DummyCompletion(text={self.text!r}, start_position={self.start_position}, display={self.display!r})"


def make_instance():
    # Avoid running AutoCompleter.__init__ to keep tests deterministic and lightweight.
    inst = object.__new__(AutoCompleter)
    # Provide defaults expected/used by get_completions
    inst.words = set()
    inst.fname_to_rel_fnames = {}
    return inst


def test_get_completions_no_words_round_020(monkeypatch):
    """When document is empty, get_completions yields nothing (covers early return at empty words).
    """
    monkeypatch.setattr(io_module, "Completion", DummyCompletion)

    inst = make_instance()

    # Ensure tokenize is called but results in no words
    def tokenize_no_words():
        inst.words = set()
        inst.fname_to_rel_fnames = {}

    inst.tokenize = tokenize_no_words

    doc = DummyDoc("")

    results = list(AutoCompleter.get_completions(inst, doc, None))
    assert results == [], "Expected no completions for empty input"


def test_get_completions_trailing_space_and_short_round_020(monkeypatch):
    """Trailing space should stop completion and short last_word (<3) should stop completion.
    """
    monkeypatch.setattr(io_module, "Completion", DummyCompletion)

    inst = make_instance()

    # tokenize sets some words, but trailing space should cause immediate return
    def tokenize_some_words():
        inst.words = {"Alpha", "Beta"}
        inst.fname_to_rel_fnames = {"Alpha": ["alpha.md"]}

    inst.tokenize = tokenize_some_words

    # trailing space case
    doc_space = DummyDoc("abc ")
    results_space = list(AutoCompleter.get_completions(inst, doc_space, None))
    assert results_space == [], "Trailing space should prevent completions"

    # short last_word (<3) case
    doc_short = DummyDoc("ab")
    results_short = list(AutoCompleter.get_completions(inst, doc_short, None))
    assert results_short == [], "Short last word (<3) should prevent completions"


def test_get_completions_command_yield_round_020(monkeypatch):
    """If get_command_completions yields, those completions are returned and normal completion is skipped.
    """
    monkeypatch.setattr(io_module, "Completion", DummyCompletion)

    inst = make_instance()

    # keep tokenize minimal
    def tokenize_dummy():
        inst.words = {"/doit"}
        inst.fname_to_rel_fnames = {"/doit": ["doit.md"]}

    inst.tokenize = tokenize_dummy

    # create a bound generator method that yields one command completion
    def get_cmds(self, document, complete_event, text, words):
        yield DummyCompletion("/doit-cmd", start_position=-len(text), display="/doit-cmd")

    inst.get_command_completions = types.MethodType(get_cmds, inst)

    doc = DummyDoc("/do")
    results = list(AutoCompleter.get_completions(inst, doc, None))

    assert len(results) == 1
    comp = results[0]
    # Ensure the yielded object is our DummyCompletion and values derive from generator
    assert isinstance(comp, DummyCompletion)
    assert comp.text == "/doit-cmd"
    assert comp.display == "/doit-cmd"
    # start_position should be negative length of the provided text
    assert comp.start_position == -len(doc.text_before_cursor)


def test_get_completions_command_exception_fallthrough_round_020(monkeypatch):
    """If get_command_completions raises CommandCompletionException, get_completions falls back to normal completion.
    This covers the exception branch and the normal matching + rel_fnames expansion + yielding sorted completions.
    """
    monkeypatch.setattr(io_module, "Completion", DummyCompletion)

    inst = make_instance()

    # Setup tokenize to provide a candidate and a rel filename
    def tokenize_with_candidates():
        # include a candidate that begins with '/abc' so it matches the last_word
        inst.words = {"/abcdef", "Other"}
        inst.fname_to_rel_fnames = {"/abcdef": ["path/to/rel1.md"]}

    inst.tokenize = tokenize_with_candidates

    # Simulate get_command_completions raising the CommandCompletionException
    def get_cmds_raise(self, document, complete_event, text, words):
        raise CommandCompletionException("forced")

    inst.get_command_completions = types.MethodType(get_cmds_raise, inst)

    doc = DummyDoc("/abc")
    results = list(AutoCompleter.get_completions(inst, doc, None))

    # We expect at least two completions: the matching word and its rel_fname expansion
    assert any(isinstance(r, DummyCompletion) for r in results), "Expected DummyCompletion results"

    # Build a mapping from text -> (start_position, display) for easy assertions
    mapping = {r.text: (r.start_position, r.display) for r in results}

    # The inserted start position must be -len(last_word)
    last_word = doc.text_before_cursor.split()[-1]
    expected_pos = -len(last_word)

    # Check the primary match is present and correctly formed
    assert "/abcdef" in mapping
    assert mapping["/abcdef"][0] == expected_pos
    assert mapping["/abcdef"][1] == "/abcdef"

    # Check the rel filename expansion is present
    assert "path/to/rel1.md" in mapping
    assert mapping["path/to/rel1.md"][0] == expected_pos
    assert mapping["path/to/rel1.md"][1] == "path/to/rel1.md"
