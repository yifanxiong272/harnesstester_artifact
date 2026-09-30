import builtins
import types
from types import SimpleNamespace
from pathlib import Path
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select import submit as submit_mod
from rdagent.scenarios.data_science.proposal.exp_gen.select.submit import select_on_existing_trace


class DummyFile:
    def __init__(self):
        self.written = ""
    def write(self, s):
        self.written += s
    def read(self):
        return ""
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def close(self):
        pass


def test_select_on_existing_trace_yaml_job_match_round_014(monkeypatch):
    """
    Exercise the branch where trace_root contains 'yaml', a job in the YAML matches the competition,
    extract_tar is called, execution proceeds to the non-debug (log) branch, multiprocessing_wrapper
    returns a hit list and the result file is attempted to be written. Assertions check that extract_tar
    was called with the expected path and that a results write was attempted.
    """

    # Prepare job info returned by yaml.safe_load
    job_info = [
        {
            "submit_args": {"env": {"DS_COMPETITION": "comp1", "RD_RES_NAME": "resname"}},
            "results_dir": "resdir",
        }
    ]

    # Patch yaml.safe_load in the module under test to return our job_info without reading files
    monkeypatch.setattr(submit_mod, "yaml", SimpleNamespace(safe_load=lambda f: job_info))

    # Ensure os.getenv used in the module returns the competition name when competition is not passed
    monkeypatch.setattr(submit_mod.os, "getenv", lambda k: "comp1")

    # Record extract_tar calls
    recorded = {}

    def fake_extract_tar(path_arg):
        # store the string form for assertion
        recorded["tar_called_with"] = str(path_arg)

    monkeypatch.setattr(submit_mod, "extract_tar", fake_extract_tar)

    # Fake Path.iterdir() for Path('log') to yield a single directory that is acceptable
    class FakeLogDir:
        def is_dir(self):
            return True
        @property
        def name(self):
            return "mylog"
        def __truediv__(self, other):
            return Path("/unused")

    # Replace Path.iterdir to return our fake log dir when invoked on Path('log')
    orig_iterdir = submit_mod.Path.iterdir

    def fake_iterdir(self):
        # If called on Path('log'), return our fake log directory
        if str(self) == "log":
            return iter([FakeLogDir()])
        # Otherwise, fallback to original behavior (safe for tests)
        return orig_iterdir(self)

    monkeypatch.setattr(submit_mod.Path, "iterdir", fake_iterdir, raising=False)

    # Fake FileStorage to return a list with one message-like object having a .content attribute
    class FakeMsg:
        def __init__(self, content):
            self.content = content

    class FakeFileStorage:
        def __init__(self, path):
            self.path = path
        def iter_msg(self, tag="trace"):
            return [FakeMsg({"some": "trace_content"})]

    monkeypatch.setattr(submit_mod, "FileStorage", FakeFileStorage)

    # Fake multiprocessing_wrapper to return a deterministic hit list
    def fake_mw(tasks, n=1):
        # return list of tuples (comp, hit, medal_info)
        return [("validation", 2, {"medal": "info"})]

    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", fake_mw)

    # Prevent actual file I/O by patching builtins.open and Path.exists (for the final rmtree check)
    last_open = {}

    def fake_open(file, mode="r", *args, **kwargs):
        # record filename and mode
        last_open["file"] = str(file)
        last_open["mode"] = mode
        return DummyFile()

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(submit_mod.Path, "exists", lambda self: False)

    # Call function under test. trace_root contains 'yaml' to trigger yaml branch
    select_on_existing_trace(
        selector_name="myselector",
        trace_root="some_yaml_path_with_yaml",
        experiment="exp1",
        competition=None,
        debug=True,
        only_sample=False,
        sample_code_path="",
        sample_rate=0.5,
    )

    # Assertions: extract_tar must have been called with the constructed path
    assert "tar_called_with" in recorded
    assert recorded["tar_called_with"].endswith("/resdir/resname")

    # Assertions: function should have attempted to open a result file for writing
    assert last_open.get("file") is not None
    assert last_open.get("mode") == "w"


def test_select_on_existing_trace_debug_no_tasks_round_014(monkeypatch):
    """
    Exercise the debug branch where no trace folders are yielded (empty iterdir), which leads to
    no tasks being created and the function returning early after logging an error. This test
    verifies the early-return path is taken and that multiprocessing_wrapper is not invoked.
    """

    # Make Path.iterdir for the provided trace_root return an empty iterator
    def empty_iterdir(self):
        return iter([])

    monkeypatch.setattr(submit_mod.Path, "iterdir", empty_iterdir, raising=False)

    # Replace multiprocessing_wrapper with a function that would fail the test if called
    def fail_if_called(*args, **kwargs):
        raise AssertionError("multiprocessing_wrapper should not be called when no tasks are present")

    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", fail_if_called)

    # Ensure no real file writes: patch builtins.open to a dummy just in case
    monkeypatch.setattr(builtins, "open", lambda *a, **k: DummyFile())

    # Also ensure Path.exists doesn't trigger rmtree (no side effects)
    monkeypatch.setattr(submit_mod.Path, "exists", lambda self: False)

    # Call with debug=True and a trace_root that does not include 'yaml' and yields no folders
    result = select_on_existing_trace(
        selector_name="sel2",
        trace_root="no_yaml_here",
        experiment="",
        competition=None,
        debug=True,
        only_sample=False,
        sample_code_path="",
        sample_rate=0.8,
    )

    # The function should return None and not raise
    assert result is None
