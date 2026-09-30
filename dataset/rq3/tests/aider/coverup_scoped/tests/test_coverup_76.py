# file: aider/run_cmd.py:11-23
# asked: {"lines": [14, 17, 18, 19, 20, 22, 23], "branches": [[13, 14], [19, 20], [19, 22]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23], "branches": [[13, 14], [19, 20], [19, 22]]}

import importlib
import sys
import types
import pytest

def _reload_module():
    # Ensure a fresh import of the module under test for each test
    if "aider.run_cmd" in sys.modules:
        importlib.reload(sys.modules["aider.run_cmd"])
    return importlib.import_module("aider.run_cmd")

def test_run_cmd_uses_pexpect_path(monkeypatch):
    arun = _reload_module()

    # Make sys.stdin.isatty() return True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    # Ensure the module's pexpect has a spawn attribute
    if not hasattr(arun.pexpect, "spawn"):
        monkeypatch.setattr(arun.pexpect, "spawn", lambda *a, **k: None, raising=False)

    # Ensure platform.system() != "Windows" within the module
    monkeypatch.setattr(arun.platform, "system", lambda: "Linux")

    called = {}
    def fake_pexpect(cmd, verbose_arg, cwd_arg):
        called["cmd"] = cmd
        called["verbose"] = verbose_arg
        called["cwd"] = cwd_arg
        return (0, "pexpect-used")

    # Patch run_cmd_pexpect and make run_cmd_subprocess raise if called
    monkeypatch.setattr(arun, "run_cmd_pexpect", fake_pexpect)
    def fake_subprocess(*a, **k):
        raise AssertionError("run_cmd_subprocess should not be called when pexpect path is taken")
    monkeypatch.setattr(arun, "run_cmd_subprocess", fake_subprocess)

    result = arun.run_cmd("echo hi", verbose=True, cwd="/tmp")
    assert result == (0, "pexpect-used")
    assert called["cmd"] == "echo hi"
    assert called["verbose"] is True
    assert called["cwd"] == "/tmp"

def test_run_cmd_handles_oserror_print_and_callback(monkeypatch, capsys):
    arun = _reload_module()

    # Force the code path to use run_cmd_subprocess by making isatty False
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    # Replace run_cmd_subprocess so it raises OSError
    def raise_oserror(*a, **k):
        raise OSError("boom")
    monkeypatch.setattr(arun, "run_cmd_subprocess", raise_oserror)

    # Case 1: error_print is None -> message printed and returned
    result = arun.run_cmd("mycmd")
    captured = capsys.readouterr()
    expected_message = "Error occurred while running command 'mycmd': boom"
    assert expected_message in captured.out
    assert result == (1, expected_message)

    # Case 2: error_print provided -> callback called and nothing printed
    collected = []
    def cb(msg):
        collected.append(msg)

    result2 = arun.run_cmd("othercmd", error_print=cb)
    captured2 = capsys.readouterr()
    expected2 = "Error occurred while running command 'othercmd': boom"
    assert collected == [expected2]
    assert captured2.out == ""
    assert result2 == (1, expected2)
