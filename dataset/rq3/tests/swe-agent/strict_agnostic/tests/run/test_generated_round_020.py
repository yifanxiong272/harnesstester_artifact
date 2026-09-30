import json
from types import SimpleNamespace
from pathlib import Path
import logging
import pytest

from sweagent.run.run_batch import RunBatch


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.errors = []

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


def _make_runbatch_instance(tmp_path, instance_id="test", redo_existing=False, logger=None):
    """Create a RunBatch instance without calling __init__ and set only the attributes
    needed by should_skip. This avoids running unrelated initialization logic.
    """
    inst = object.__new__(RunBatch)
    inst._redo_existing = redo_existing
    inst.output_dir = tmp_path
    inst.logger = logger or DummyLogger()
    inst.problem_statement = SimpleNamespace(id=instance_id)
    return inst


def _traj_path(tmp_path, instance_id):
    return tmp_path / instance_id / (instance_id + ".traj")


def test_redo_existing_round_020(tmp_path):
    rb = _make_runbatch_instance(tmp_path, redo_existing=True)
    # When redo_existing is True, should_skip short-circuits to False (line ~380-381).
    result = rb.should_skip(SimpleNamespace(problem_statement=SimpleNamespace(id="ignored")))
    assert result is False


def test_no_log_exists_round_020(tmp_path):
    rb = _make_runbatch_instance(tmp_path, redo_existing=False)
    # Ensure no file exists -> should_skip returns False (lines ~384-386)
    inst = SimpleNamespace(problem_statement=SimpleNamespace(id="no_file"))
    result = rb.should_skip(inst)
    assert result is False


def test_empty_trajectory_round_020(tmp_path):
    logger = DummyLogger()
    rb = _make_runbatch_instance(tmp_path, redo_existing=False, logger=logger)
    tid = "empty"
    p = _traj_path(tmp_path, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("   \n  \t  ")

    inst = SimpleNamespace(problem_statement=SimpleNamespace(id=tid))
    result = rb.should_skip(inst)

    # The function should detect empty content, warn, unlink the file, and return False
    assert result is False
    assert not p.exists()
    # logger warning should have been called at least once
    assert logger.warnings, "expected a warning for empty trajectory"


def test_invalid_json_round_020(tmp_path):
    logger = DummyLogger()
    rb = _make_runbatch_instance(tmp_path, redo_existing=False, logger=logger)
    tid = "invalid_json"
    p = _traj_path(tmp_path, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not a json")

    inst = SimpleNamespace(problem_statement=SimpleNamespace(id=tid))
    result = rb.should_skip(inst)

    # Invalid JSON should cause the exception branch: error logged, file removed, False returned
    assert result is False
    assert not p.exists()
    assert logger.errors, "expected an error logged for invalid json"


def test_exit_status_none_round_020(tmp_path):
    logger = DummyLogger()
    rb = _make_runbatch_instance(tmp_path, redo_existing=False, logger=logger)
    tid = "no_status"
    p = _traj_path(tmp_path, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"info": {}}))

    inst = SimpleNamespace(problem_statement=SimpleNamespace(id=tid))
    result = rb.should_skip(inst)

    # Missing exit_status should be treated as incomplete: warning, remove, return False
    assert result is False
    assert not p.exists()
    assert logger.warnings, "expected a warning when exit_status is None"


def test_exit_status_early_exit_round_020(tmp_path):
    logger = DummyLogger()
    rb = _make_runbatch_instance(tmp_path, redo_existing=False, logger=logger)
    tid = "early_exit"
    p = _traj_path(tmp_path, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"info": {"exit_status": "early_exit"}}))

    inst = SimpleNamespace(problem_statement=SimpleNamespace(id=tid))
    result = rb.should_skip(inst)

    # early_exit is treated as incomplete: warning, remove, return False
    assert result is False
    assert not p.exists()
    assert logger.warnings, "expected a warning for early_exit"


def test_exit_status_present_round_020(tmp_path):
    logger = DummyLogger()
    rb = _make_runbatch_instance(tmp_path, redo_existing=False, logger=logger)
    tid = "done"
    p = _traj_path(tmp_path, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"info": {"exit_status": "success"}}))

    inst = SimpleNamespace(problem_statement=SimpleNamespace(id=tid))
    result = rb.should_skip(inst)

    # If a valid exit_status exists, we expect it to be returned and the file to remain
    assert result == "success"
    assert p.exists()
    assert logger.infos, "expected an info log for skipping an existing trajectory"
