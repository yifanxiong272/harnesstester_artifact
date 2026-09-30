# file: aider/run_cmd.py:26-39
# asked: {"lines": [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39], "branches": [[29, 30], [31, 32], [31, 33], [34, 35], [34, 36]]}
# gained: {"lines": [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39], "branches": [[29, 30], [31, 32], [31, 33], [34, 35], [34, 36]]}

import pytest
import psutil

from aider import run_cmd


class FakeProc:
    def __init__(self, name=None, parent=None):
        self._name = name
        self._parent = parent

    def parent(self):
        return self._parent

    def name(self):
        return self._name


def test_returns_powershell_when_in_ancestors(monkeypatch):
    # Build a chain: child -> mid -> powershell
    powershell = FakeProc(name="PowerShell.EXE", parent=None)
    mid = FakeProc(name="someprocess.exe", parent=powershell)
    child = FakeProc(name="child.exe", parent=mid)

    monkeypatch.setattr(psutil, "Process", lambda: child)

    result = run_cmd.get_windows_parent_process_name()
    assert result == "powershell.exe"


def test_returns_none_when_no_matching_parent(monkeypatch):
    # Parent is None immediately
    child = FakeProc(name="child.exe", parent=None)
    monkeypatch.setattr(psutil, "Process", lambda: child)

    result = run_cmd.get_windows_parent_process_name()
    assert result is None


def test_returns_none_on_exception_creating_process(monkeypatch):
    # Make psutil.Process raise an exception to exercise the except branch
    def raise_on_create():
        raise RuntimeError("cannot create process")

    monkeypatch.setattr(psutil, "Process", raise_on_create)

    result = run_cmd.get_windows_parent_process_name()
    assert result is None
