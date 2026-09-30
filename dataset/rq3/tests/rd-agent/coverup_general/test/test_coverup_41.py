# file: rdagent/log/ui/ds_trace.py:201-245
# asked: {"lines": [201, 202, 203, 204, 205, 206, 207, 209, 210, 212, 213, 215, 216, 217, 218, 219, 220, 221, 222, 223, 226, 227, 228, 229, 231, 233, 234, 235, 237, 238, 239, 240, 241, 242, 243, 245], "branches": [[203, 204], [203, 245], [204, 205], [204, 209], [217, 218], [217, 226], [226, 0], [226, 227], [233, 0], [233, 234], [234, 235], [234, 237], [239, 240], [239, 243]]}
# gained: {"lines": [201, 202, 203, 204, 205, 206, 207, 209, 210, 212, 213, 215, 216, 217, 218, 219, 220, 221, 222, 223, 226, 227, 228, 229, 231, 233, 234, 235, 237, 238, 239, 240, 241, 242, 243, 245], "branches": [[203, 204], [203, 245], [204, 205], [204, 209], [217, 218], [217, 226], [226, 0], [226, 227], [233, 234], [234, 235], [234, 237], [239, 240], [239, 243]]}

import importlib
import sys
import os
from pathlib import Path

import pytest


class DummySessionStateBeforeImport:
    """
    Minimal mapping-like session_state replacement used at import time to satisfy
    module-level checks in rdagent.log.ui.ds_trace. Implements containment,
    item access and attribute access.
    """
    def __init__(self):
        self._d = {
            "log_folders": ["./log"],
            "log_folder": Path("./log"),
            "show_stdout": False,
            "show_llm_log": False,
            "data": {},
        }

    def __contains__(self, key):
        return key in self._d

    def __iter__(self):
        return iter(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __getattr__(self, name):
        # allow attribute-style access like state.log_folders
        if name in self._d:
            return self._d[name]
        raise AttributeError(name)

    def __setitem__(self, key, value):
        self._d[key] = value

    def __setattr__(self, name, value):
        if name == "_d":
            super().__setattr__(name, value)
        else:
            self._d[name] = value


class Recorder:
    def __init__(self):
        self.popovers = []
        self.codes = []
        self.writes = []
        self.tabs_called = []
        self.markdowns = []
        self.text_input_returns = ""
        self.button_returns = False
        self.warnings = []
        self.successes = []
        self.last_popover_kwargs = []
        self.tabs_generated = []

    def popover(self, *args, **kwargs):
        self.popovers.append((args, kwargs))
        self.last_popover_kwargs.append((args, kwargs))
        return DummyCM(self)

    def code(self, content, **kwargs):
        self.codes.append((content, kwargs))

    def write(self, *args, **kwargs):
        self.writes.append((args, kwargs))

    def tabs(self, keys):
        keys_list = list(keys)
        self.tabs_called.append(keys_list)
        cms = [DummyCM(self) for _ in keys_list]
        self.tabs_generated = cms
        return cms

    def markdown(self, content, **kwargs):
        self.markdowns.append(content)

    def text_input(self, label, key=None):
        return self.text_input_returns

    def button(self, label, key=None):
        return self.button_returns

    def warning(self, msg):
        self.warnings.append(msg)

    def success(self, msg):
        self.successes.append(msg)


class DummyCM:
    def __init__(self, recorder):
        self.recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SimpleRunningInfo:
    def __init__(self, running_time):
        self.running_time = running_time


class Workspace:
    def __init__(self, file_dict, running_time=0, workspace_path="/wspace"):
        self.file_dict = file_dict
        self.running_info = SimpleRunningInfo(running_time)
        self.workspace_path = workspace_path


def import_ds_with_dummy_state(monkeypatch):
    """
    Ensure streamlit.session_state is set to a minimal object before importing
    rdagent.log.ui.ds_trace, to avoid AttributeError at module import time.
    Return the imported module.
    """
    import streamlit
    monkeypatch.setattr(streamlit, "session_state", DummySessionStateBeforeImport(), raising=False)

    # Ensure we reload module to pick up patched session_state
    sys.modules.pop("rdagent.log.ui.ds_trace", None)
    ds = importlib.import_module("rdagent.log.ui.ds_trace")
    return ds


def setup_common_after_import(monkeypatch, ds):
    """
    After importing ds module, replace st and state and helper functions used by workspace_win.
    Return Recorder instance.
    """
    rec = Recorder()
    # Replace streamlit st object inside module
    monkeypatch.setattr(ds, "st", rec, raising=True)

    # Create a simple state for workspace_win usage
    class State:
        show_save_input = False

    monkeypatch.setattr(ds, "state", State, raising=True)

    # Replace helpers used in workspace_win to deterministic behaviors
    monkeypatch.setattr(ds, "replace_ep_path", lambda x: f"REPLACED:{x}", raising=True)
    monkeypatch.setattr(ds, "timedelta_to_str", lambda td: "00:00:05" if td else None, raising=True)

    return rec


def test_workspace_win_with_cmp_and_no_save(monkeypatch):
    ds = import_ds_with_dummy_state(monkeypatch)
    rec = setup_common_after_import(monkeypatch, ds)

    # Prepare workspaces
    ws_files = {
        "main.py": "print('hello')",
        "README.md": "# readme",
        "test_ignore.py": "should be filtered"
    }
    cmp_files = {"main.py": "print('old')"}
    workspace = Workspace(ws_files, running_time=5, workspace_path="/home/user/proj")
    cmp_workspace = Workspace(cmp_files, running_time=0, workspace_path="/home/user/proj_old")

    called = {}

    def fake_generate_diff(a, b, fname):
        called['args'] = (a, b, fname)
        return ["-old\n", "+new\n"]

    monkeypatch.setattr(ds, "generate_diff_from_dict", fake_generate_diff, raising=True)

    # Ensure save input is not shown
    ds.state.show_save_input = False

    # Run
    ds.workspace_win(workspace, cmp_workspace=cmp_workspace, cmp_name="last commit")

    # Assertions
    assert 'args' in called
    assert called['args'][0] == cmp_files
    expected_show_files = {k: v for k, v in ws_files.items() if "test" not in k}
    assert called['args'][1] == expected_show_files
    assert called['args'][2] == "main.py"
    # The diff should have been sent to st.code once (for diff)
    assert any("+new" in c[0] or "-old" in c[0] for c in rec.codes)
    # The files' contents should also have been rendered via st.code (for each tab)
    assert len(rec.codes) >= 1 + len(expected_show_files)
    # The popover for files should have been called (time + path)
    assert any("Files in" in args[0] or "⏱️" in args[0] for args, kwargs in rec.popovers)


def test_workspace_win_save_flow_empty_and_nonempty(monkeypatch, tmp_path):
    ds = import_ds_with_dummy_state(monkeypatch)
    rec = setup_common_after_import(monkeypatch, ds)

    # Workspace with files (saving uses workspace.file_dict)
    ws_files = {
        "main.py": "print('save_me')",
        "subdir/notes.md": "notes",
        "test_only.py": "ignored_in_tabs_but_saved"
    }
    workspace = Workspace(ws_files, running_time=0, workspace_path="/app")

    # No cmp_workspace provided for this test
    ds.state.show_save_input = True

    # First scenario: empty target folder -> warning
    rec.text_input_returns = "   "  # whitespace => treated as empty after strip
    rec.button_returns = True  # user clicked save

    ds.workspace_win(workspace, cmp_workspace=None)

    assert any("Please enter a valid folder path." in w for w in rec.warnings), rec.warnings

    # Second scenario: valid target folder -> files written
    target = tmp_path / "outfolder"
    rec.text_input_returns = str(target)
    rec.button_returns = True
    rec.warnings.clear()
    rec.successes.clear()

    ds.workspace_win(workspace, cmp_workspace=None)

    for fname, content in ws_files.items():
        p = target / fname
        assert p.exists(), f"Expected file {p} to exist"
        read = p.read_text(encoding="utf-8")
        assert read == content

    assert any("All files saved to" in s for s in rec.successes)

    # Cleanup explicitly (tmp_path will be cleaned by pytest, but remove contents)
    for root, dirs, files in os.walk(str(target), topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if target.exists():
        os.rmdir(str(target))


def test_workspace_win_no_files(monkeypatch):
    ds = import_ds_with_dummy_state(monkeypatch)
    rec = setup_common_after_import(monkeypatch, ds)

    ws_files = {"test_only.py": "ignored"}
    workspace = Workspace(ws_files, running_time=0, workspace_path="/emptyproj")

    ds.state.show_save_input = False

    ds.workspace_win(workspace, cmp_workspace=None)

    assert any("No files in" in m for m in rec.markdowns), rec.markdowns
