import types
import pytest
from types import SimpleNamespace
import aider.linter as linter

# All test function names end with _round_070

def test_no_lang_round_070(monkeypatch):
    # filename_to_lang returns falsy -> early return (lines 206-208)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: None)
    res = linter.basic_lint("file.unknown", "some code")
    assert res is None


def test_typescript_lang_round_070(monkeypatch):
    # filename_to_lang returns "typescript" -> early return (lines 210-212)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "typescript")
    res = linter.basic_lint("file.ts", "let x: number = 1;")
    assert res is None


def test_get_parser_raises_round_070(monkeypatch, capsys):
    # get_parser raises -> prints message and returns None (lines 214-218)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    def raise_exc(lang):
        raise Exception("boom")

    monkeypatch.setattr(linter, "get_parser", raise_exc)
    res = linter.basic_lint("file.py", "x = 1")
    captured = capsys.readouterr()
    assert "Unable to load parser: boom" in captured.out
    assert res is None


def test_traverse_recursionerror_round_070(monkeypatch, capsys):
    # parser.parse succeeds but traverse_tree raises RecursionError (lines 222-226)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, b):
            # ensure the code was passed as bytes
            assert isinstance(b, (bytes, bytearray))
            return SimpleNamespace(root_node="ROOT")

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())
    monkeypatch.setattr(linter, "traverse_tree", lambda node: (_ for _ in ()).throw(RecursionError()))

    fname = "file.py"
    res = linter.basic_lint(fname, "x = 1")
    captured = capsys.readouterr()
    assert f"Unable to lint {fname} due to RecursionError" in captured.out
    assert res is None


def test_no_errors_round_070(monkeypatch):
    # traverse_tree returns empty list -> function returns None (lines 228-229)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, b):
            return SimpleNamespace(root_node="ROOT")

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())
    monkeypatch.setattr(linter, "traverse_tree", lambda node: [])

    res = linter.basic_lint("file.py", "")
    assert res is None


def test_with_errors_returns_lintresult_round_070(monkeypatch):
    # traverse_tree returns non-empty list -> returns LintResult (line 231)
    monkeypatch.setattr(linter, "filename_to_lang", lambda fname: "python")

    class FakeParser:
        def parse(self, b):
            return SimpleNamespace(root_node="ROOT")

    monkeypatch.setattr(linter, "get_parser", lambda lang: FakeParser())
    expected_errors = [10, 20, 30]
    monkeypatch.setattr(linter, "traverse_tree", lambda node: expected_errors)

    res = linter.basic_lint("file.py", "some code")
    # result should be an instance of LintResult with text=="" and lines == expected_errors
    assert res is not None
    assert hasattr(res, "text") and hasattr(res, "lines")
    assert res.text == ""
    assert res.lines == expected_errors
