# file: aider/linter.py:201-231
# asked: {"lines": [206, 207, 208, 211, 212, 214, 215, 216, 217, 218, 220, 222, 223, 224, 225, 226, 228, 229, 231], "branches": [[207, 208], [207, 211], [211, 212], [211, 214], [228, 229], [228, 231]]}
# gained: {"lines": [206, 207, 208, 211, 212, 214, 215, 216, 217, 218, 220, 222, 223, 224, 225, 226, 228, 229, 231], "branches": [[207, 208], [207, 211], [211, 212], [211, 214], [228, 229], [228, 231]]}

import types
import pytest

import aider.linter as linter


def _make_parser(tree):
    class Parser:
        def parse(self, b):
            return tree
    return Parser()


class DummyTree:
    def __init__(self, root_node=None):
        self.root_node = root_node


def test_basic_lint_no_lang(monkeypatch):
    # filename_to_lang returns falsy -> basic_lint returns None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: None)
    # Ensure other functions would error if called (they should not be)
    monkeypatch.setattr(linter, "get_parser", lambda lang: (_ for _ in ()).throw(RuntimeError("should not be called")))
    res = linter.basic_lint("some.unknown", "code")
    assert res is None


def test_basic_lint_typescript_shortcircuits(monkeypatch):
    # filename_to_lang returns 'typescript' -> short-circuit return None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "typescript")
    called = {"get_parser": False}
    def get_parser(lang):
        called["get_parser"] = True
        return None
    monkeypatch.setattr(linter, "get_parser", get_parser)
    res = linter.basic_lint("file.ts", "var a: number;")
    assert res is None
    assert not called["get_parser"]  # parser should not be requested for typescript


def test_basic_lint_get_parser_raises_prints_and_returns(monkeypatch, capsys):
    # filename_to_lang returns a lang, but get_parser raises Exception
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")
    def bad_get_parser(lang):
        raise Exception("boom")
    monkeypatch.setattr(linter, "get_parser", bad_get_parser)
    res = linter.basic_lint("file.py", "print('hi')")
    captured = capsys.readouterr()
    assert "Unable to load parser: boom" in captured.out
    assert res is None


def test_basic_lint_traverse_raises_recursionerror(monkeypatch, capsys):
    # get_parser returns a parser; parse returns tree; traverse_tree raises RecursionError
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")
    tree = DummyTree(root_node="root")
    monkeypatch.setattr(linter, "get_parser", lambda lang: _make_parser(tree))
    def raise_rec(node):
        raise RecursionError("too deep")
    monkeypatch.setattr(linter, "traverse_tree", raise_rec)
    res = linter.basic_lint("file.py", "x = 1")
    captured = capsys.readouterr()
    assert "Unable to lint file.py due to RecursionError" in captured.out
    assert res is None


def test_basic_lint_no_errors_returns_none(monkeypatch):
    # traverse_tree returns empty list -> function returns None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")
    tree = DummyTree(root_node="root")
    monkeypatch.setattr(linter, "get_parser", lambda lang: _make_parser(tree))
    monkeypatch.setattr(linter, "traverse_tree", lambda node: [])
    res = linter.basic_lint("file.py", "ok = True")
    assert res is None


def test_basic_lint_with_errors_returns_lintresult(monkeypatch):
    # traverse_tree returns errors -> function returns a LintResult instance
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")
    tree = DummyTree(root_node="root")
    monkeypatch.setattr(linter, "get_parser", lambda lang: _make_parser(tree))
    errors = ["E1", "E2"]
    monkeypatch.setattr(linter, "traverse_tree", lambda node: errors)

    # Patch LintResult to a simple class we can inspect
    class DummyLintResult:
        def __init__(self, text, lines):
            self.text = text
            self.lines = lines

        def __repr__(self):
            return f"DummyLintResult(text={self.text!r}, lines={self.lines!r})"

    monkeypatch.setattr(linter, "LintResult", DummyLintResult)

    res = linter.basic_lint("file.py", "broken code")
    assert isinstance(res, DummyLintResult)
    assert res.text == ""
    assert res.lines == errors
