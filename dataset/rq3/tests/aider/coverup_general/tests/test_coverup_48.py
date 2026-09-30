# file: aider/linter.py:118-134
# asked: {"lines": [119, 120, 121, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134], "branches": [[125, 126], [125, 133], [126, 127], [126, 128], [128, 129], [128, 130], [133, 0], [133, 134]]}
# gained: {"lines": [119, 120, 121, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134], "branches": [[125, 126], [125, 133], [126, 127], [126, 128], [128, 129], [128, 130], [133, 0], [133, 134]]}

import types
import pytest

import aider.linter as linter_module
from aider.linter import Linter, LintResult


def test_py_lint_all_none(monkeypatch):
    """
    If basic_lint, lint_python_compile and flake8_lint all return falsy,
    py_lint should return None.
    """
    # Arrange: patch the three lint functions/methods to return None
    monkeypatch.setattr(linter_module, "basic_lint", lambda rel_fname, code: None)
    monkeypatch.setattr(linter_module, "lint_python_compile", lambda fname, code: None)
    monkeypatch.setattr(Linter, "flake8_lint", lambda self, rel_fname: None)

    # Act
    res = Linter().py_lint("some/file.py", "file.py", "print('ok')")

    # Assert
    assert res is None


def test_py_lint_concat_and_lines(monkeypatch):
    """
    Exercise the loop where multiple results are concatenated with a newline
    and their line sets are combined.
    """
    # Create fake result objects
    basic = types.SimpleNamespace(text="BASIC_MSG", lines={1, 2})
    compile = None  # simulate a falsy compile result to hit the 'continue' branch
    flake = types.SimpleNamespace(text="FLAKE_MSG", lines={3})

    # Patch module functions/methods
    monkeypatch.setattr(linter_module, "basic_lint", lambda rel_fname, code: basic)
    monkeypatch.setattr(linter_module, "lint_python_compile", lambda fname, code: compile)
    monkeypatch.setattr(Linter, "flake8_lint", lambda self, rel_fname: flake)

    # Act
    res = Linter().py_lint("some/file.py", "file.py", "print('ok')")

    # Assert: a LintResult should be returned with combined text and lines
    assert isinstance(res, LintResult)
    # Combined text should be BASIC_MSG\nFLAKE_MSG (newline inserted between non-empty texts)
    assert res.text == "BASIC_MSG\nFLAKE_MSG"
    # Lines should be union of both sets
    assert res.lines == {1, 2, 3}


def test_py_lint_empty_text_but_lines(monkeypatch):
    """
    If a result has empty text but non-empty lines, the function should still
    return a LintResult because 'lines' is truthy.
    """
    basic = types.SimpleNamespace(text="", lines={42})
    monkeypatch.setattr(linter_module, "basic_lint", lambda rel_fname, code: basic)
    monkeypatch.setattr(linter_module, "lint_python_compile", lambda fname, code: None)
    monkeypatch.setattr(Linter, "flake8_lint", lambda self, rel_fname: None)

    res = Linter().py_lint("some/file.py", "file.py", "bad code")

    assert isinstance(res, LintResult)
    # Text should be empty string (since only res.text was empty)
    assert res.text == ""
    # Lines should contain the line reported
    assert res.lines == {42}
