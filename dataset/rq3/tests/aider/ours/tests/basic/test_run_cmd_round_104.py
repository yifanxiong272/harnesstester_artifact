import pytest
import aider.run_cmd as run_cmd


def test_parent_none_round_104(monkeypatch):
    """If the current process has no parent, function should return None."""
    class FakeProcess:
        def parent(self):
            return None

    # Patch Process to return our fake process instance
    monkeypatch.setattr(run_cmd.psutil, "Process", lambda: FakeProcess())

    assert run_cmd.get_windows_parent_process_name() is None


def test_immediate_powershell_round_104(monkeypatch):
    """If an immediate parent has name 'PowerShell.EXE' (different case), it is lowercased and returned."""
    class FakeParent:
        def name(self):
            return "PowerShell.EXE"

    class FakeProcess:
        def parent(self):
            return FakeParent()

    monkeypatch.setattr(run_cmd.psutil, "Process", lambda: FakeProcess())

    assert run_cmd.get_windows_parent_process_name() == "powershell.exe"


def test_chain_non_matching_then_none_round_104(monkeypatch):
    """If parent chain exists but none match the target names, return None after walking the chain."""
    class ParentLeaf:
        def __init__(self, parent):
            self._parent = parent

        def name(self):
            return "explorer.exe"

        def parent(self):
            return self._parent

    class RootProcess:
        def parent(self):
            # Return a parent whose parent is None (chain length 1)
            return ParentLeaf(None)

    monkeypatch.setattr(run_cmd.psutil, "Process", lambda: RootProcess())

    assert run_cmd.get_windows_parent_process_name() is None


def test_process_raises_exception_round_104(monkeypatch):
    """If psutil.Process() raises, the function should catch and return None."""
    def raising_proc():
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(run_cmd.psutil, "Process", raising_proc)

    assert run_cmd.get_windows_parent_process_name() is None
