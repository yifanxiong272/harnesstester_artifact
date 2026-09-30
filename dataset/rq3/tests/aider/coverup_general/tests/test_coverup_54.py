# file: aider/linter.py:177-198
# asked: {"lines": [178, 179, 180, 181, 182, 183, 185, 186, 188, 189, 190, 191, 192, 193, 195, 197, 198], "branches": [[190, 191], [190, 195], [191, 190], [191, 192]]}
# gained: {"lines": [178, 179, 181, 182, 183, 185, 186, 188, 189, 190, 191, 192, 193, 195, 197, 198], "branches": [[190, 191], [191, 190], [191, 192]]}

import builtins
import traceback

import pytest

from aider.linter import lint_python_compile, LintResult


def test_lint_python_compile_truncates_traceback_and_reports_line_numbers():
    # Create code with a syntax error at line 2 (missing colon)
    bad_code = "x = 1\nif True\n    pass\n"

    res = lint_python_compile("somefile.py", bad_code)

    # Should return a LintResult instance with the offending line index (0-based)
    assert isinstance(res, LintResult)
    assert res.lines == [1]  # error reported at line 2 -> index 1

    # The returned text should contain the Traceback header but not the source line
    # from aider.linter that contained the marker (it should have been removed)
    assert "Traceback (most recent call last):" in res.text
    assert "# USE TRACEBACK BELOW HERE" not in res.text


def test_lint_python_compile_uses_end_lineno_and_handles_traceback(monkeypatch):
    # This test forces compile to raise an exception that has both lineno and end_lineno
    def fake_compile(code, fname, mode):
        # Create a SyntaxError instance and attach lineno and end_lineno
        e = SyntaxError("fake syntax")
        # Set multiline error: lineno=2, end_lineno=5 -> expect indices [1,2,3,4]
        e.lineno = 2
        e.end_lineno = 5
        # Raise it so it has an actual traceback that includes the call site
        raise e

    # Monkeypatch builtins.compile used by aider.linter
    monkeypatch.setattr(builtins, "compile", fake_compile)

    res = lint_python_compile("ignored.py", "irrelevant")

    # Cleanup: monkeypatch will restore builtins.compile automatically after test

    assert isinstance(res, LintResult)
    # Expect zero-based line indices from lineno-1 up to end_lineno-1
    assert res.lines == [1, 2, 3, 4]

    # The traceback header should remain
    assert "Traceback (most recent call last):" in res.text
    # The marker line from the source should have been located and used to trim the traceback
    assert "# USE TRACEBACK BELOW HERE" not in res.text
    # The formatted exception message should mention "fake syntax"
    assert "fake syntax" in res.text
