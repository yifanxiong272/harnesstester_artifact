import pytest

import aider.linter as linter_mod
from aider.linter import Linter


class _DummyResult:
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr


def test_flake8_lint_no_errors_round_132(monkeypatch):
    """When subprocess.run produces no stdout or stderr, flake8_lint should return None.

    This covers the branch where errors is falsy and the function returns early.
    """
    l = Linter(encoding="utf-8", root=".")

    # Patch subprocess.run used by the module to return an object with empty stdout/stderr
    monkeypatch.setattr(
        linter_mod.subprocess,
        "run",
        lambda *a, **kw: _DummyResult("", ""),
    )

    # Call with a sample relative filename
    rel = "some_file.py"
    result = l.flake8_lint(rel)

    # When there are no errors, the function should return None (early exit)
    assert result is None


def test_flake8_lint_with_stdout_errors_round_132(monkeypatch):
    """When subprocess.run returns output, flake8_lint should call errors_to_lint_result with
    the constructed running header and the returned errors, and return its result.
    """
    l = Linter(encoding="utf-8", root="/tmp")

    # Make subprocess.run return a deterministic stdout containing an example flake8 message
    monkeypatch.setattr(
        linter_mod.subprocess,
        "run",
        lambda *a, **kw: _DummyResult("example_error:1:1: E999 dummy\n", ""),
    )

    captured = {}

    def fake_errors_to_lint_result(rel_fname, text):
        # capture arguments so assertions can inspect them
        captured['rel_fname'] = rel_fname
        captured['text'] = text
        return {"from": "errors_to_lint_result", "fname": rel_fname}

    # Patch the instance method so we avoid depending on other Linter behavior
    l.errors_to_lint_result = fake_errors_to_lint_result

    rel = "project/file.py"
    ret = l.flake8_lint(rel)

    # Should return the sentinel from our patched errors_to_lint_result
    assert ret == {"from": "errors_to_lint_result", "fname": rel}

    # Verify the rel_fname was passed through unchanged
    assert captured['rel_fname'] == rel

    # The text should include the Running header and the error content
    assert captured['text'].startswith("## Running:"), "expected running header in text"
    assert "example_error:1:1: E999 dummy" in captured['text']


def test_flake8_lint_subprocess_raises_round_132(monkeypatch):
    """When subprocess.run raises, flake8_lint should catch and include the exception message
    in the constructed text passed to errors_to_lint_result.
    """
    l = Linter(encoding="utf-8", root="/tmp")

    # Make subprocess.run raise deterministically
    def raise_run(*a, **kw):
        raise RuntimeError("boom-fail")

    monkeypatch.setattr(linter_mod.subprocess, "run", raise_run)

    captured = {}

    def fake_errors_to_lint_result(rel_fname, text):
        captured['rel_fname'] = rel_fname
        captured['text'] = text
        return "SENTINEL"

    l.errors_to_lint_result = fake_errors_to_lint_result

    rel = "another.py"
    ret = l.flake8_lint(rel)

    # Ensure we return what the patched errors_to_lint_result returns
    assert ret == "SENTINEL"

    # The text should include the error prefix and the exception message
    assert captured['rel_fname'] == rel
    assert "Error running flake8:" in captured['text']
    assert "boom-fail" in captured['text']
