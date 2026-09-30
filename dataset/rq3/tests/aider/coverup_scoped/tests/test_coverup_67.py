# file: aider/commands.py:1447-1474
# asked: {"lines": [1450, 1451, 1456, 1457, 1458, 1459, 1460, 1461, 1466], "branches": [[1449, 1450], [1465, 1466]]}
# gained: {"lines": [1450, 1451, 1456, 1457, 1458, 1459, 1460, 1461, 1466], "branches": [[1449, 1450], [1465, 1466]]}

import builtins
import io as _io
import os
from types import SimpleNamespace

import pytest

from aider.commands import Commands, SwitchCoder


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []
        self.encoding = "utf-8"

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


def test_cmd_load_empty_args():
    io = DummyIO()
    cmd = Commands(io, coder=None)
    # whitespace-only argument should trigger the "please provide filename" path
    cmd.cmd_load("   ")
    assert io.errors == ["Please provide a filename containing commands to load."]
    assert io.outputs == []


def test_cmd_load_file_not_found(monkeypatch):
    io = DummyIO()
    cmd = Commands(io, coder=None)

    # Force open to raise FileNotFoundError to exercise that except branch.
    def raising_open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(builtins, "open", raising_open)
    cmd.cmd_load("no_such_file.txt")
    assert io.errors == ["File not found: no_such_file.txt"]
    assert io.outputs == []


def test_cmd_load_error_reading(monkeypatch):
    io = DummyIO()
    cmd = Commands(io, coder=None)

    def raising_open(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(builtins, "open", raising_open)
    cmd.cmd_load("somefile")
    # Expect the generic error reading file message with the exception text included
    assert io.errors == ["Error reading file: boom"]
    assert io.outputs == []


def test_cmd_load_process_commands(tmp_path):
    io = DummyIO()
    cmd = Commands(io, coder=None)

    # Create a commands file containing blank line, comment, and two commands.
    p = tmp_path / "commands.txt"
    p.write_text("\n# a comment\n do_ok\n do_switch\n")

    run_calls = []

    # Replace the run method on this Commands instance to track calls and raise SwitchCoder for a specific command.
    def fake_run(c):
        # Should not be called with blank or comment; only with stripped commands.
        run_calls.append(c)
        if c == "do_switch":
            raise SwitchCoder()
        # else succeed

    # Assign the fake run method
    cmd.run = fake_run

    cmd.cmd_load(str(p))
    # Ensure the blank and comment lines were skipped (run_calls should contain only 'do_ok' and 'do_switch')
    assert run_calls == ["do_ok", "do_switch"]
    # Ensure outputs include the Executing lines for both commands
    assert any("Executing: do_ok" in out for out in io.outputs)
    assert any("Executing: do_switch" in out for out in io.outputs)
    # Ensure SwitchCoder produced the expected tool_error message for the interactive-only command
    assert f"Command 'do_switch' is only supported in interactive mode, skipping." in io.errors
