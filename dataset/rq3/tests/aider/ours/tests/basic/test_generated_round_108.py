import io
import sys
import importlib
import builtins
import pytest

import aider.diffs as diffs


def test_main_usage_message_round_108(monkeypatch, capsys):
    """When argv length != 3, main should print usage and exit with code 1."""
    # Arrange: ensure sys.argv length is not 3
    monkeypatch.setattr(sys, "argv", ["prog"], raising=True)

    # Act / Assert
    with pytest.raises(SystemExit) as excinfo:
        diffs.main()
    assert excinfo.value.code == 1

    out = capsys.readouterr().out
    assert "Usage: python diffs.py file1 file" in out


def test_main_process_files_round_108(monkeypatch, capsys):
    """Exercise the file-processing path: open files, call diff_partial_update repeatedly,
    print results and call input() each iteration (patched to no-op).

    This test patches:
    - builtins.open to provide deterministic file contents for two filenames
    - aider.diffs.diff_partial_update to a local stub so we can assert behavior
    - builtins.input to avoid blocking
    - sys.argv to point at our fake files
    """
    # Prepare argv so that main will try to open the two files
    argv = ["prog", "orig.txt", "updated.txt"]
    monkeypatch.setattr(sys, "argv", argv, raising=True)

    # Deterministic file contents
    orig_text = "orig_line1\norig_line2\n"
    updated_text = "upd_line1\n"

    # Keep real open to delegate unexpected paths
    real_open = builtins.open

    def open_mock(path, mode="r", encoding=None):
        # match the call sites in main which pass encoding="utf-8"
        if path == "orig.txt":
            return io.StringIO(orig_text)
        if path == "updated.txt":
            return io.StringIO(updated_text)
        # fallback to the real open for any other path
        if encoding is None:
            return real_open(path, mode)
        return real_open(path, mode, encoding=encoding)

    # Patch builtins.open where main will resolve it
    monkeypatch.setattr(builtins, "open", open_mock, raising=True)

    # Track calls to diff_partial_update and return a predictable string based on length
    calls = []

    def diff_stub(lines_orig, lines_updated_slice):
        # record copies to make assertions deterministic and avoid aliasing
        calls.append((list(lines_orig), list(lines_updated_slice)))
        return f"R:{len(lines_updated_slice)}"

    # Patch the function in the module where main resolves it
    monkeypatch.setattr(diffs, "diff_partial_update", diff_stub, raising=True)

    # Patch input so main doesn't block waiting for user input
    monkeypatch.setattr(builtins, "input", lambda: "", raising=True)

    # Act
    diffs.main()

    # Capture printed output lines
    out = capsys.readouterr().out
    printed_lines = [ln for ln in out.splitlines()]

    # The loop in main uses range(len(file_updated)) where file_updated is the filename string
    expected_iterations = len(argv[2])  # len("updated.txt")

    # Assertions about number of iterations and printed outputs
    assert len(printed_lines) == expected_iterations
    # First call gets a slice of length 0
    assert printed_lines[0] == "R:0"
    # All subsequent prints should show the updated slice size (updated_text has 1 line)
    assert all(p == "R:1" for p in printed_lines[1:])

    # Ensure diff_partial_update was called expected number of times
    assert len(calls) == expected_iterations
    # Make a couple of spot checks on the recorded call arguments
    # first call -> 0-length updated slice
    assert calls[0][1] == []
    # second call -> one-line updated slice
    if expected_iterations >= 2:
        assert calls[1][1] == ["upd_line1\n"]
