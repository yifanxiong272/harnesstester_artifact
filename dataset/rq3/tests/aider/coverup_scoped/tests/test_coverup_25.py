# file: aider/linter.py:136-168
# asked: {"lines": [137, 138, 140, 141, 142, 143, 144, 145, 148, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 161, 162, 164, 165, 167, 168], "branches": [[164, 165], [164, 167]]}
# gained: {"lines": [137, 138, 140, 141, 142, 143, 144, 145, 148, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 161, 162, 164, 165, 167, 168], "branches": [[164, 165], [164, 167]]}

import sys
from types import SimpleNamespace
import pytest

from aider.linter import Linter


def test_flake8_lint_no_errors_returns_none(monkeypatch):
    l = Linter()

    # stub subprocess.run to simulate no output (no errors)
    def fake_run(cmd, capture_output, text, check, encoding, errors, cwd):
        # verify arguments passed through
        assert isinstance(cmd, list)
        assert cmd[0] == sys.executable
        assert cmd[1] == "-m"
        assert cmd[2] == "flake8"
        # select option should be present
        select_opts = [c for c in cmd if c.startswith("--select=")]
        assert select_opts, "Expected --select option in flake8 command"
        assert capture_output is True
        assert text is True
        assert check is False
        assert encoding == l.encoding
        assert errors == "replace"
        assert cwd == l.root
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr("aider.linter.subprocess.run", fake_run)

    # Should return None when there are no errors
    result = l.flake8_lint("some_file.py")
    assert result is None


def test_flake8_lint_with_stdout_returns_lint_result(monkeypatch):
    l = Linter()

    # simulate flake8 producing output on stdout
    def fake_run(cmd, capture_output, text, check, encoding, errors, cwd):
        return SimpleNamespace(stdout="E999 some error\nline\n", stderr="")

    monkeypatch.setattr("aider.linter.subprocess.run", fake_run)

    captured = {}

    def fake_errors_to_lint_result(rel_fname, text):
        # capture inputs for assertions and return a sentinel
        captured["rel_fname"] = rel_fname
        captured["text"] = text
        return ("SENTINEL", rel_fname)

    # Replace instance method
    monkeypatch.setattr(l, "errors_to_lint_result", fake_errors_to_lint_result)

    result = l.flake8_lint("path/to/file.py")
    assert result == ("SENTINEL", "path/to/file.py")
    assert captured["rel_fname"] == "path/to/file.py"
    # text should include the running command header and the flake8 output
    assert captured["text"].startswith("## Running: ")
    assert "E999 some error" in captured["text"]


def test_flake8_lint_subprocess_exception_returns_lint_result(monkeypatch):
    l = Linter()

    # make subprocess.run raise an exception
    def fake_run_raise(cmd, capture_output, text, check, encoding, errors, cwd):
        raise RuntimeError("boom")

    monkeypatch.setattr("aider.linter.subprocess.run", fake_run_raise)

    captured = {}

    def fake_errors_to_lint_result(rel_fname, text):
        captured["rel_fname"] = rel_fname
        captured["text"] = text
        return {"result": "error", "fname": rel_fname}

    monkeypatch.setattr(l, "errors_to_lint_result", fake_errors_to_lint_result)

    result = l.flake8_lint("other.py")
    assert result == {"result": "error", "fname": "other.py"}
    assert captured["rel_fname"] == "other.py"
    # The error text should mention the exception message
    assert "Error running flake8: boom" in captured["text"]
    # And the header should still be present
    assert captured["text"].startswith("## Running: ")
