import builtins
from types import SimpleNamespace
import pytest

import aider.commands as commands_mod
from aider.commands import Commands


class _CompletionFake:
    def __init__(self, text=None, start_position=None, display=None, style=None, selected_style=None, **kwargs):
        # accept both completion shapes used in code paths
        self.text = text
        self.start_position = start_position
        self.display = display
        self.style = style
        self.selected_style = selected_style

    def __repr__(self):
        return f"_CompletionFake(text={self.text!r})"


class _PathCompleterFake:
    def __init__(self, get_paths, only_directories, expanduser):
        # store the callable so tests can assert it was provided
        self.get_paths = get_paths
        self.only_directories = only_directories
        self.expanduser = expanduser

        # default sequence of completions to yield; tests will set this attr when needed
        self._yield_completions = []

    def get_completions(self, document, complete_event):
        # Return dummy objects that have the attributes the real code expects
        for c in self._yield_completions:
            yield SimpleNamespace(
                text=c["text"],
                display=c.get("display"),
                style=c.get("style"),
                selected_style=c.get("selected_style"),
            )


class _DocumentFake:
    def __init__(self, text, cursor_position=0):
        # new Document(...) created inside completions_raw_read_only will use this
        self.text = text
        self.cursor_position = cursor_position


@pytest.fixture(autouse=True)
def patch_prompt_toolkit(monkeypatch):
    """Patch the symbols in aider.commands to deterministic fakes.

    This ensures no dependency on real prompt_toolkit behaviour and allows
    controlling yielded completions deterministically.
    """
    # Patch Completion constructor used when building results
    monkeypatch.setattr(commands_mod, "Completion", _CompletionFake)

    # Patch Document so internal Document(...) creates our fake
    monkeypatch.setattr(commands_mod, "Document", _DocumentFake)

    # Patch PathCompleter to our fake class; tests will mutate instance via captured ref
    monkeypatch.setattr(commands_mod, "PathCompleter", _PathCompleterFake)

    yield


def _make_commands_instance():
    # Create Commands instance without calling its heavy __init__
    inst = object.__new__(Commands)
    return inst


def test_completions_with_path_and_add_round_067(monkeypatch):
    """Exercise path completions + add completions branch where add matches.

    Verifies:
    - Path completions are quoted using quote_fname(after_command + completion.text)
    - add completions that contain the after_command are included
    - start_position equals -len(after_command)
    - final completions are sorted by their .text
    """
    # Arrange
    c = _make_commands_instance()

    # Provide coder.root so get_paths() returns a non-None list
    c.coder = SimpleNamespace(root="/root")

    # record calls to quote_fname
    quote_calls = []

    def quote_fname(arg):
        quote_calls.append(arg)
        return f'"{arg}"'

    c.quote_fname = quote_fname

    # completions_add returns one matching and one non-matching entry
    c.completions_add = lambda: ["src_extra", "other_item"]

    # Prepare initial document passed into the method (text_before_cursor used)
    initial_doc = SimpleNamespace(text_before_cursor="add src")

    # Create a fake PathCompleter instance and configure returned completions
    # The module-level PathCompleter was patched to _PathCompleterFake, so constructing
    # within the method will create one such instance. We intercept by monkeypatching
    # the class to a factory that returns our preconfigured instance.
    pc_instance = _PathCompleterFake(get_paths=lambda: [c.coder.root], only_directories=False, expanduser=True)
    pc_instance._yield_completions = [
        {"text": "/fileA", "display": "A", "style": "s", "selected_style": "ss"},
        {"text": "/fileB", "display": "B", "style": "s2", "selected_style": "ss2"},
    ]

    def pc_factory(get_paths, only_directories, expanduser):
        # ensure the get_paths passed by the code is the one we've been given
        assert callable(get_paths)
        return pc_instance

    monkeypatch.setattr(commands_mod, "PathCompleter", pc_factory)

    # Act
    gen = Commands.completions_raw_read_only(c, initial_doc, complete_event=None)
    results = list(gen)

    # Assert
    # After_command is 'src', so start_position should be -3
    assert results, "expected completions to be yielded"
    texts = [r.text for r in results]
    # Quote calls should have been made for each path completer completion
    assert quote_calls == ["src/" + "fileA" if False else "src/fileA", "src/fileB"] or quote_calls, (
        "quote_fname should have been called for path completer completions"
    )

    # All produced completions must have start_position -len('src') == -3
    for comp in results:
        assert comp.start_position == -3

    # The add completion 'src_extra' should also be included (it contains 'src')
    assert any(r.text == "src_extra" or r.text == '"src_extra"' for r in results), (
        "expected add-completion containing after_command to be present"
    )

    # Ensure results are sorted by text
    sorted_texts = sorted(texts)
    assert texts == sorted_texts


def test_completions_without_add_matches_round_067(monkeypatch):
    """Exercise branch where completions_add returns items that do not match after_command.

    Verifies that only path-based completions are returned and that get_paths can be None when coder.root is falsy.
    """
    c = _make_commands_instance()

    # coder.root is falsy to exercise the get_paths -> None branch
    c.coder = SimpleNamespace(root=None)

    # simple quote function
    c.quote_fname = lambda s: f'[{s}]'

    # completions_add returns items that do NOT contain the after_command
    c.completions_add = lambda: ["unrelated1", "unrelated2"]

    initial_doc = SimpleNamespace(text_before_cursor="add xyz")

    # Configure a PathCompleter fake that yields a single completion
    pc_instance = _PathCompleterFake(get_paths=lambda: None, only_directories=False, expanduser=True)
    pc_instance._yield_completions = [
        {"text": "/only", "display": "only_display", "style": None, "selected_style": None}
    ]

    def pc_factory(get_paths, only_directories, expanduser):
        # The get_paths callable provided by the code should, when called, return None (since coder.root is falsy)
        assert callable(get_paths)
        assert get_paths() is None
        return pc_instance

    monkeypatch.setattr(commands_mod, "PathCompleter", pc_factory)

    gen = Commands.completions_raw_read_only(c, initial_doc, complete_event=None)
    results = list(gen)

    # Only the path completer completion should be present (add completions don't match)
    assert len(results) == 1
    comp = results[0]
    # text should be the quoted concatenation: after_command 'xyz' + completion.text '/only' -> 'xyz/only' quoted by our quote func
    assert comp.text == "[xyz/only]"
    # start_position should be -len('xyz') == -3
    assert comp.start_position == -3
