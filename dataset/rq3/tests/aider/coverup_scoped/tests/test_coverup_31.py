# file: aider/linter.py:118-134
# asked: {"lines": [119, 120, 121, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134], "branches": [[125, 126], [125, 133], [126, 127], [126, 128], [128, 129], [128, 130], [133, 0], [133, 134]]}
# gained: {"lines": [119, 120, 121, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134], "branches": [[125, 126], [125, 133], [126, 127], [126, 128], [128, 129], [128, 130], [133, 134]]}

import pytest
from types import SimpleNamespace

import aider.linter as linter_mod
from aider.linter import Linter, LintResult


def test_py_lint_combines_texts_and_lines(monkeypatch):
    # Arrange: stub basic_lint, lint_python_compile, and Linter.flake8_lint
    def basic_stub(rel_fname, code):
        return LintResult("basic", [1])

    def compile_stub(fname, code):
        return LintResult("compile", [2])

    def flake_stub(self, rel_fname):
        return LintResult("flake", [3])

    monkeypatch.setattr(linter_mod, "basic_lint", basic_stub)
    monkeypatch.setattr(linter_mod, "lint_python_compile", compile_stub)
    monkeypatch.setattr(Linter, "flake8_lint", flake_stub)

    lntr = Linter()
    # Act
    res = lntr.py_lint("file.py", "file.py", "code")

    # Assert
    assert isinstance(res, LintResult)
    # Texts should be joined with newlines in order basic -> compile -> flake
    assert res.text == "basic\ncompile\nflake"
    # Lines should be the set union of provided line numbers
    assert isinstance(res.lines, set)
    assert res.lines == {1, 2, 3}


def test_py_lint_handles_empty_texts_and_none_results(monkeypatch):
    # Arrange:
    # basic returns an empty text but has a line number
    def basic_stub(rel_fname, code):
        return LintResult("", [5])

    # compile returns None to exercise the 'if not res: continue' path
    def compile_stub(fname, code):
        return None

    # flake returns non-empty text but no lines
    def flake_stub(self, rel_fname):
        return LintResult("flakeonly", [])

    monkeypatch.setattr(linter_mod, "basic_lint", basic_stub)
    monkeypatch.setattr(linter_mod, "lint_python_compile", compile_stub)
    monkeypatch.setattr(Linter, "flake8_lint", flake_stub)

    lntr = Linter()
    # Act
    res = lntr.py_lint("another.py", "another.py", "some code")

    # Assert: should still return because lines exist (from basic_stub)
    assert isinstance(res, LintResult)
    # Text should be 'flakeonly' (empty basic text doesn't add a leading newline)
    assert res.text == "flakeonly"
    # Lines should contain the single line from basic_stub
    assert res.lines == {5}
