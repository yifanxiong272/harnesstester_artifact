# file: aider/linter.py:201-231
# asked: {"lines": [206, 207, 208, 211, 212, 214, 215, 216, 217, 218, 220, 222, 223, 224, 225, 226, 228, 229, 231], "branches": [[207, 208], [207, 211], [211, 212], [211, 214], [228, 229], [228, 231]]}
# gained: {"lines": [206, 207, 208, 211, 212, 214, 215, 216, 217, 218, 220, 222, 223, 224, 225, 226, 228, 229, 231], "branches": [[207, 208], [207, 211], [211, 212], [211, 214], [228, 229], [228, 231]]}

import builtins
from collections import namedtuple

import pytest

import aider.linter as linter


def test_basic_lint_no_lang(monkeypatch):
    # filename_to_lang returns falsy -> early return
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: None)
    result = linter.basic_lint("file.unknown", "some code")
    assert result is None


def test_basic_lint_typescript_short_circuit(monkeypatch):
    # filename_to_lang indicates typescript -> early return
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "typescript")
    result = linter.basic_lint("file.ts", "let x: number = 1;")
    assert result is None


def test_basic_lint_get_parser_raises(monkeypatch, capsys):
    # get_parser raises -> prints message and returns None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    def raise_parser(lang):
        raise RuntimeError("parser missing")

    monkeypatch.setattr(linter, "get_parser", raise_parser)
    result = linter.basic_lint("file.py", "print('hi')")

    captured = capsys.readouterr()
    assert "Unable to load parser" in captured.out
    # ensure exception detail is included
    assert "parser missing" in captured.out
    assert result is None


def test_basic_lint_traverse_recursion(monkeypatch, capsys):
    # traverse_tree raises RecursionError -> prints message and returns None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, data_bytes):
            class Tree:
                pass

            t = Tree()
            t.root_node = object()
            return t

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())

    def raise_recursion(root):
        raise RecursionError("too deep")

    monkeypatch.setattr(linter, "traverse_tree", raise_recursion)

    result = linter.basic_lint("deep_file.py", "def f(): pass")

    captured = capsys.readouterr()
    assert "Unable to lint deep_file.py due to RecursionError" in captured.out
    assert result is None


def test_basic_lint_no_errors(monkeypatch):
    # traverse_tree returns empty list -> basic_lint returns None
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, data_bytes):
            class Tree:
                pass

            t = Tree()
            t.root_node = object()
            return t

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())
    monkeypatch.setattr(linter, "traverse_tree", lambda root: [])

    result = linter.basic_lint("clean.py", "a = 1")
    assert result is None


def test_basic_lint_with_errors_returns_lintresult(monkeypatch):
    # traverse_tree returns non-empty list -> basic_lint returns a LintResult
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, data_bytes):
            class Tree:
                pass

            t = Tree()
            t.root_node = object()
            return t

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())

    errors = ["line 1: error", "line 2: another error"]
    monkeypatch.setattr(linter, "traverse_tree", lambda root: errors)

    # Provide a simple LintResult type for the function to construct
    LintResult = namedtuple("LintResult", ["text", "lines"])
    monkeypatch.setattr(linter, "LintResult", LintResult)

    result = linter.basic_lint("bad.py", "bad code")
    assert isinstance(result, LintResult)
    assert result.text == ""
    assert result.lines == errors
