import builtins
import pytest

import aider.linter as linter


def test_lint_python_compile_finds_target_round_083(monkeypatch):
    """When the formatted traceback contains the special target marker,
    lint_python_compile should slice out the intervening traceback lines
    and return a LintResult with the expected text and line numbers.
    """
    # Create a synthetic exception instance with lineno and end_lineno
    err = Exception("compile failure simulated")
    err.lineno = 3
    err.end_lineno = 6

    # Patch the builtin compile to raise our synthetic exception
    def fake_compile(code, fname, mode):
        raise err

    monkeypatch.setattr(builtins, "compile", fake_compile)

    # Provide a controlled traceback.format_exception output that includes the marker
    tb_lines = [
        "Traceback (most recent call last):\n",
        "  File \"<string>\", line 3\n",
        "    some code # USE TRACEBACK BELOW HERE\n",
        "  File \"other\", line 1\n",
        "    other context\n",
    ]

    monkeypatch.setattr(linter.traceback, "format_exception", lambda *a, **k: tb_lines)

    res = linter.lint_python_compile("fake_file.py", "irrelevant code")

    # After finding the marker at index 2, the function keeps the first line and everything after index 2
    expected_text = "".join([tb_lines[0]] + tb_lines[3:])
    assert isinstance(res, linter.LintResult)
    assert res.text == expected_text

    # lines should be range(err.lineno - 1, err.end_lineno) => range(2,6) -> [2,3,4,5]
    assert res.lines == [2, 3, 4, 5]


def test_lint_python_compile_no_target_round_083(monkeypatch):
    """When the formatted traceback does not include the target marker,
    lint_python_compile should return the original formatted traceback and
    line numbers computed from lineno only (no end_lineno attribute).
    """
    err = Exception("another compile failure")
    # Only provide lineno; end_lineno should fall back to lineno
    err.lineno = 2

    def fake_compile(code, fname, mode):
        raise err

    monkeypatch.setattr(builtins, "compile", fake_compile)

    # Traceback without the marker
    tb_lines = ["Traceback (most recent call last):\n", "  File \"<string>\", line 2\n    bad\n"]
    monkeypatch.setattr(linter.traceback, "format_exception", lambda *a, **k: tb_lines)

    res = linter.lint_python_compile("file.py", "bad code")

    # When target not found, tb_lines should remain unchanged (after the slice operation)
    expected_text = "".join(tb_lines)
    assert isinstance(res, linter.LintResult)
    assert res.text == expected_text

    # end_lineno missing -> use err.lineno; lines == list(range(1,2)) -> [1]
    assert res.lines == [1]
