# file: sweagent/run/run_batch.py:376-409
# asked: {"lines": [381, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 400, 401, 402, 403, 405, 406, 408, 409], "branches": [[380, 381], [385, 388], [389, 390], [389, 394], [398, 399], [398, 408]]}
# gained: {"lines": [381, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 400, 401, 402, 403, 405, 406, 408, 409], "branches": [[380, 381], [385, 388], [389, 390], [389, 394], [398, 399], [398, 408]]}

import json
import types
from pathlib import Path

import pytest

from sweagent.run.run_batch import RunBatch


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.errors = []

    def warning(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except Exception:
            # fallback for f-strings passed as single argument
            formatted = msg
        self.warnings.append(formatted)

    def info(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except Exception:
            formatted = msg
        self.infos.append(formatted)

    def error(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except Exception:
            formatted = msg
        self.errors.append(formatted)


def make_instance(id_str: str):
    return types.SimpleNamespace(problem_statement=types.SimpleNamespace(id=id_str))


def make_runbatch(tmp_path: Path, redo_existing: bool):
    # create an instance of RunBatch without calling its __init__
    rb = object.__new__(RunBatch)
    rb._redo_existing = redo_existing
    rb.output_dir = tmp_path
    rb.logger = DummyLogger()
    return rb


def traj_path_for(tmp_path: Path, id_str: str) -> Path:
    d = tmp_path / id_str
    d.mkdir(parents=True, exist_ok=True)
    return d / (id_str + ".traj")


def test_should_skip_with_redo_existing_returns_false(tmp_path):
    rb = make_runbatch(tmp_path, redo_existing=True)
    inst = make_instance("p_redo")
    result = rb.should_skip(inst)
    assert result is False
    # nothing created
    assert not (tmp_path / "p_redo").exists()


def test_should_skip_empty_traj_is_removed_and_returns_false(tmp_path):
    rb = make_runbatch(tmp_path, redo_existing=False)
    inst = make_instance("p_empty")
    p = traj_path_for(tmp_path, inst.problem_statement.id)
    p.write_text("   \n\t")  # whitespace-only content

    result = rb.should_skip(inst)
    assert result is False
    # file should have been removed
    assert not p.exists()
    # logger recorded a warning about empty trajectory
    assert any("Found empty trajectory" in m for m in rb.logger.warnings)


def test_should_skip_invalid_json_logs_error_and_removes(tmp_path):
    rb = make_runbatch(tmp_path, redo_existing=False)
    inst = make_instance("p_invalid")
    p = traj_path_for(tmp_path, inst.problem_statement.id)
    p.write_text("this is not json")

    result = rb.should_skip(inst)
    assert result is False
    assert not p.exists()
    assert any("Failed to check existing trajectory" in m for m in rb.logger.errors)


def test_should_skip_none_or_early_exit_removes_and_returns_false(tmp_path):
    # exit_status is None
    rb_none = make_runbatch(tmp_path, redo_existing=False)
    inst_none = make_instance("p_none")
    p_none = traj_path_for(tmp_path, inst_none.problem_statement.id)
    p_none.write_text(json.dumps({"info": {"exit_status": None}}))

    res_none = rb_none.should_skip(inst_none)
    assert res_none is False
    assert not p_none.exists()
    assert any("no exit status" in m or "Found existing trajectory with no exit status" in m for m in rb_none.logger.warnings)

    # exit_status is "early_exit"
    rb_early = make_runbatch(tmp_path, redo_existing=False)
    inst_early = make_instance("p_early")
    p_early = traj_path_for(tmp_path, inst_early.problem_statement.id)
    p_early.write_text(json.dumps({"info": {"exit_status": "early_exit"}}))

    res_early = rb_early.should_skip(inst_early)
    assert res_early is False
    assert not p_early.exists()
    assert any("no exit status" in m or "Found existing trajectory with no exit status" in m for m in rb_early.logger.warnings)


def test_should_skip_valid_exit_status_skips_and_returns_status(tmp_path):
    rb = make_runbatch(tmp_path, redo_existing=False)
    inst = make_instance("p_success")
    p = traj_path_for(tmp_path, inst.problem_statement.id)
    p.write_text(json.dumps({"info": {"exit_status": "success"}, "other": 1}))

    result = rb.should_skip(inst)
    assert result == "success"
    # file should remain because it was considered complete
    assert p.exists()
    assert any("Skipping existing trajectory" in m or "⏭️ Skipping existing trajectory" in m for m in rb.logger.infos)
