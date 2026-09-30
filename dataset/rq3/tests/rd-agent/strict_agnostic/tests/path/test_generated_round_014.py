import builtins
from io import StringIO
import types
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select import submit as submit_mod

# Deterministic dummy Path-like used for iterdir results
class DummyPath:
    def __init__(self, name, is_dir=True):
        self.name = name
        self._is_dir = is_dir

    def is_dir(self):
        return self._is_dir

    def __truediv__(self, other):
        # Return a string-like representation for any division used in tests
        return f"{self.name}/{other}"

    def __str__(self):
        return self.name


def _dummy_open(*args, **kwargs):
    # Always return an empty text file-like object to avoid disk I/O
    return StringIO("{}")


def test_select_on_existing_trace_yaml_debug_round_014(monkeypatch):
    """
    Exercise the branch where trace_root contains 'yaml' and debug is True.
    We mock open and yaml.safe_load to return a single job that matches the provided competition,
    and mock extract_tar to observe it's called. We also mock FileStorage.iter_msg to be empty
    so the function returns early (deterministic behavior).
    """
    # Record calls
    extract_calls = []

    # Replace open so no real file I/O happens
    monkeypatch.setattr(builtins, "open", _dummy_open)

    # Mock yaml.safe_load to return a job list with submit_args matching competition
    def fake_safe_load(_file_obj):
        return [
            {
                "submit_args": {"env": {"DS_COMPETITION": "comp1", "RD_RES_NAME": "res1"}},
                "results_dir": "resdir1",
            }
        ]

    monkeypatch.setattr(submit_mod.yaml, "safe_load", fake_safe_load)

    # Observe extract_tar calls
    def fake_extract_tar(path):
        extract_calls.append(str(path))

    monkeypatch.setattr(submit_mod, "extract_tar", fake_extract_tar)

    # Provide a dummy log directory entry for the later else branch (will not produce traces)
    def fake_iterdir(self):
        return iter([DummyPath("mylog")])

    monkeypatch.setattr(submit_mod.Path, "iterdir", fake_iterdir)

    # Mock FileStorage so iter_msg yields no traces -> triggers the early return in else branch
    class DummyFileStorage:
        def __init__(self, path):
            self.path = path

        def iter_msg(self, tag="trace"):
            return iter([])

    monkeypatch.setattr(submit_mod, "FileStorage", DummyFileStorage)

    # Call function: trace_root contains 'yaml' so the yaml branch is used
    result = submit_mod.select_on_existing_trace(
        selector_name="sel",
        trace_root="some_yaml_root_with_yaml",
        experiment="exp1",
        competition="comp1",
        debug=True,
    )

    # Oracle: function should return None (early exits) and extract_tar should have been called
    assert result is None
    assert extract_calls, "extract_tar should have been invoked for the YAML job"


def test_select_on_existing_trace_no_log_traces_round_014(monkeypatch):
    """
    Exercise the non-debug branch that browses the log directory. We mock Path.iterdir to return
    exactly one directory that satisfies the 'next' generator criteria and mock FileStorage.iter_msg
    to return an empty list so the code logs an error and returns early.
    """
    # Ensure no real open on disk
    monkeypatch.setattr(builtins, "open", _dummy_open)

    # Provide a dummy log directory entry so next(...) selects it
    def fake_iterdir(self):
        return iter([DummyPath("log_ok")])

    monkeypatch.setattr(submit_mod.Path, "iterdir", fake_iterdir)

    # FileStorage that yields no traces
    class DummyFileStorage2:
        def __init__(self, path):
            self.path = path

        def iter_msg(self, tag="trace"):
            return iter([])

    monkeypatch.setattr(submit_mod, "FileStorage", DummyFileStorage2)

    # Call function: debug False path, should return None when no traces found
    result = submit_mod.select_on_existing_trace(
        selector_name="sel",
        trace_root="no_yaml_root",
        experiment=None,
        competition=None,
        debug=False,
    )

    assert result is None
