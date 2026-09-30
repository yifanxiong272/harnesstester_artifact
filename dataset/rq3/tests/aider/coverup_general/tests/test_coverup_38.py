# file: aider/linter.py:136-168
# asked: {"lines": [137, 138, 140, 141, 142, 143, 144, 145, 148, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 161, 162, 164, 165, 167, 168], "branches": [[164, 165], [164, 167]]}
# gained: {"lines": [137, 138, 140, 141, 142, 143, 144, 145, 148, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 161, 162, 164, 165, 167, 168], "branches": [[164, 165], [164, 167]]}

import sys
import types
import pytest

import aider.linter as linter_mod
from aider.linter import Linter

class DummyCompletedProcess:
    def __init__(self, stdout="", stderr=""):
        self.stdout = stdout
        self.stderr = stderr

def test_flake8_lint_no_errors(monkeypatch):
    called = {}

    def fake_run(cmd, capture_output, text, check, encoding, errors, cwd):
        # record the invocation for assertions and return empty outputs
        called['cmd'] = cmd
        called['capture_output'] = capture_output
        called['text'] = text
        called['check'] = check
        called['encoding'] = encoding
        called['errors'] = errors
        called['cwd'] = cwd
        return DummyCompletedProcess(stdout="", stderr="")

    monkeypatch.setattr(linter_mod.subprocess, "run", fake_run)

    l = Linter(encoding="utf-32", root="/some/root")
    rel = "path/to/file.py"

    # Should return None when no errors are produced
    result = l.flake8_lint(rel)
    assert result is None

    # Verify the subprocess was called with expected flake8 command structure
    cmd = called.get("cmd")
    assert isinstance(cmd, list)
    # first element is the python executable
    assert cmd[0] == sys.executable
    # contains -m flake8
    assert "-m" in cmd
    assert "flake8" in cmd
    # contains select fatal codes flag
    select_flags = [c for c in cmd if c.startswith("--select=")]
    assert select_flags, "Expected --select=... in flake8 args"
    # verify encoding and cwd were passed through
    assert called["encoding"] == "utf-32"
    assert called["cwd"] == "/some/root"

def test_flake8_lint_subprocess_exception(monkeypatch):
    recorded = {}

    def fake_run_raises(cmd, capture_output, text, check, encoding, errors, cwd):
        # record command used and then raise to trigger except branch
        recorded['cmd'] = cmd
        raise RuntimeError("boom")

    monkeypatch.setattr(linter_mod.subprocess, "run", fake_run_raises)

    l = Linter(encoding="utf-8", root=None)
    rel = "some/module.py"

    result = l.flake8_lint(rel)
    # Should return a lint result object because errors string will be non-empty
    assert result is not None
    # The header should mention the running command
    assert isinstance(result.text, str)
    assert "Running:" in result.text
    # The error message should include the exception message
    assert "Error running flake8: boom" in result.text
    # Since the error text does not include file/line info, lines should be empty list
    assert hasattr(result, "lines")
    assert result.lines == []

def test_flake8_lint_with_stdout_errors(monkeypatch):
    called = {}

    # Create a stdout that references the rel_fname with a line number
    rel = "mypkg/example.py"
    example_stdout = f"{rel}:3:1: E999 syntax error\nsome other info\n"

    def fake_run_with_errors(cmd, capture_output, text, check, encoding, errors, cwd):
        called['cmd'] = cmd
        return DummyCompletedProcess(stdout=example_stdout, stderr="")

    monkeypatch.setattr(linter_mod.subprocess, "run", fake_run_with_errors)

    l = Linter(encoding="utf-8", root=None)
    result = l.flake8_lint(rel)

    # Should return a lint result with text that includes the flake8 output
    assert result is not None
    assert example_stdout in result.text
    # The errors_to_lint_result should detect the filename and convert lineno to zero-based index
    assert hasattr(result, "lines")
    # original lineno was 3 -> zero-based should be 2
    assert result.lines == [2]
