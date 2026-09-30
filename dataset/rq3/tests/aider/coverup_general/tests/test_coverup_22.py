# file: aider/commands.py:702-757
# asked: {"lines": [704, 707, 710, 712, 713, 715, 716, 717, 718, 722, 725, 728, 729, 730, 731, 732, 733, 734, 735, 736, 741, 742, 743, 744, 745, 746, 747, 748, 753, 756, 757], "branches": [[728, 729], [728, 741], [742, 743], [742, 753], [743, 742], [743, 744], [756, 0], [756, 757]]}
# gained: {"lines": [704, 707, 710, 712, 713, 715, 716, 717, 718, 722, 725, 728, 729, 730, 731, 732, 733, 734, 735, 736, 741, 742, 743, 744, 745, 746, 747, 748, 753, 756, 757], "branches": [[728, 729], [728, 741], [742, 743], [742, 753], [743, 742], [743, 744], [756, 0], [756, 757]]}

import pytest

import aider.commands as ac


class FakePathCompletion:
    def __init__(self, text, display=None, style=None, selected_style=None):
        self.text = text
        self.display = display if display is not None else text
        self.style = style
        self.selected_style = selected_style


class FakeCompletion:
    def __init__(self, text, start_position=0, display=None, style=None, selected_style=None):
        # Mirror attributes expected by callers/tests
        self.text = text
        self.start_position = start_position
        self.display = display
        self.style = style
        self.selected_style = selected_style

    def __repr__(self):
        return f"Completion(text={self.text!r}, start_position={self.start_position!r})"


class FakePathCompleter:
    def __init__(self, get_paths=None, only_directories=False, expanduser=False):
        self._get_paths = get_paths
        try:
            self.resolved_paths = get_paths() if callable(get_paths) else None
        except Exception:
            self.resolved_paths = None
        self._to_yield = []

    def add_yield(self, text, display=None, style=None, selected_style=None):
        self._to_yield.append(FakePathCompletion(text, display, style, selected_style))

    def get_completions(self, new_document, complete_event):
        for c in self._to_yield:
            yield c


class SimpleDocument:
    def __init__(self, text, cursor_position=None):
        self.text = text
        self.cursor_position = cursor_position


def make_cmd(io=None, coder_root=None):
    class Coder:
        def __init__(self, root):
            self.root = root

    return ac.Commands(io=io, coder=Coder(coder_root))


def test_completions_raw_read_only_with_repo_root(monkeypatch):
    # Patch symbols inside aider.commands so the function uses our fakes
    monkeypatch.setattr(ac, "Completion", FakeCompletion, raising=False)
    monkeypatch.setattr(ac, "PathCompleter", FakePathCompleter, raising=False)
    monkeypatch.setattr(ac, "Document", SimpleDocument, raising=False)

    cmd = make_cmd(io=None, coder_root="/my/repo")

    # Simulate the incoming prompt_toolkit Document-like object with text_before_cursor
    class DocInput:
        text_before_cursor = "add somedir"

    document = DocInput()
    complete_event = object()

    # quote_fname should be invoked for path completions
    monkeypatch.setattr(cmd, "quote_fname", lambda s: f"Q({s})")

    # completions_add returns one match and one non-match
    monkeypatch.setattr(cmd, "completions_add", lambda: ["somedir_extra", "other"])

    # Replace PathCompleter with a factory that adds yields so get_completions returns items
    created_instances = []

    def PathCompleter_factory(get_paths=None, only_directories=False, expanduser=False):
        inst = FakePathCompleter(get_paths=get_paths, only_directories=only_directories, expanduser=expanduser)
        # Add path completions that will be quoted by quote_fname
        inst.add_yield("/a", display="A", style="s1", selected_style="ss1")
        inst.add_yield("/b", display="B", style="s2", selected_style="ss2")
        created_instances.append(inst)
        return inst

    monkeypatch.setattr(ac, "PathCompleter", PathCompleter_factory, raising=False)

    gen = cmd.completions_raw_read_only(document, complete_event)
    results = list(gen)

    # Expect two path completions + one matching add completion
    assert len(results) == 3

    expected_start = -len("somedir")
    for comp in results:
        assert hasattr(comp, "start_position")
        assert comp.start_position == expected_start

    # Ensure two path completions were quoted
    path_texts = [c.text for c in results if isinstance(c.text, str) and c.text.startswith("Q(")]
    assert len(path_texts) == 2
    assert any("somedir/a" in t or "somedir/b" in t for t in path_texts)

    # Ensure add completion present
    add_texts = [c.text for c in results if c.text == "somedir_extra"]
    assert add_texts == ["somedir_extra"]

    # Verify PathCompleter resolved the repo root
    assert created_instances, "PathCompleter was not created"
    inst = created_instances[-1]
    assert inst.resolved_paths == [cmd.coder.root]


def test_completions_raw_read_only_with_no_repo_root(monkeypatch):
    # Patch symbols inside aider.commands so the function uses our fakes
    monkeypatch.setattr(ac, "Completion", FakeCompletion, raising=False)
    monkeypatch.setattr(ac, "PathCompleter", FakePathCompleter, raising=False)
    monkeypatch.setattr(ac, "Document", SimpleDocument, raising=False)

    cmd = make_cmd(io=None, coder_root=None)

    class DocInput:
        text_before_cursor = "add x"

    document = DocInput()
    complete_event = object()

    # quote_fname noop
    monkeypatch.setattr(cmd, "quote_fname", lambda s: s)
    monkeypatch.setattr(cmd, "completions_add", lambda: ["x_match"])

    created = []

    def PathCompleter_none(get_paths=None, only_directories=False, expanduser=False):
        inst = FakePathCompleter(get_paths=get_paths, only_directories=only_directories, expanduser=expanduser)
        created.append(inst)
        return inst

    monkeypatch.setattr(ac, "PathCompleter", PathCompleter_none, raising=False)

    gen = cmd.completions_raw_read_only(document, complete_event)
    results = list(gen)

    # Only the add completion should be present
    assert len(results) == 1
    comp = results[0]
    assert comp.text == "x_match"
    assert comp.start_position == -1

    # PathCompleter get_paths should have resolved to None since coder.root is falsy
    assert created, "PathCompleter was not created"
    assert created[-1].resolved_paths is None
