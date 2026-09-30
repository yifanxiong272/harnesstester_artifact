# file: sweagent/run/run_batch.py:376-409
# asked: {"lines": [381, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 400, 401, 402, 403, 405, 406, 408, 409], "branches": [[380, 381], [385, 388], [389, 390], [389, 394], [398, 399], [398, 408]]}
# gained: {"lines": [381, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 400, 401, 402, 403, 405, 406, 408, 409], "branches": [[380, 381], [385, 388], [389, 390], [389, 394], [398, 399], [398, 408]]}

import json
from pathlib import Path
import pytest

from sweagent.run.run_batch import RunBatch


class DummyProblemStatement:
    def __init__(self, id_):
        self.id = id_


class DummyInstance:
    def __init__(self, id_):
        self.problem_statement = DummyProblemStatement(id_)


class DummyLogger:
    def __init__(self):
        self.warning_calls = []
        self.error_calls = []
        self.info_calls = []

    def warning(self, *args, **kwargs):
        self.warning_calls.append(args)

    def error(self, *args, **kwargs):
        self.error_calls.append(args)

    def info(self, *args, **kwargs):
        self.info_calls.append(args)


def make_fake_self(tmp_path: Path, redo_existing: bool):
    fake = type("FakeSelf", (), {})()
    fake._redo_existing = redo_existing
    fake.output_dir = tmp_path
    fake.logger = DummyLogger()
    return fake


def write_traj_file(dirpath: Path, id_: str, content: str):
    d = dirpath / id_
    d.mkdir(parents=True, exist_ok=True)
    p = d / (id_ + ".traj")
    p.write_text(content)
    return p


def test_should_skip_respects_redo_existing(tmp_path):
    # When _redo_existing is True, should_skip should return False immediately and not touch files.
    fake = make_fake_self(tmp_path, redo_existing=True)
    inst = DummyInstance("prob1")
    # Create a trajectory file that would otherwise cause skipping
    p = write_traj_file(tmp_path, "prob1", json.dumps({"info": {"exit_status": "done"}}))
    result = RunBatch.should_skip(fake, inst)
    assert result is False
    # File must remain untouched because we returned early
    assert p.exists()
    # No logger calls should have been made
    assert fake.logger.warning_calls == []
    assert fake.logger.error_calls == []
    assert fake.logger.info_calls == []


def test_should_skip_empty_trajectory_removes_file_and_logs(tmp_path):
    fake = make_fake_self(tmp_path, redo_existing=False)
    inst = DummyInstance("prob_empty")
    p = write_traj_file(tmp_path, "prob_empty", "   \n\t")
    assert p.exists()
    result = RunBatch.should_skip(fake, inst)
    assert result is False
    # File should be removed
    assert not p.exists()
    # Warning should have been called with the formatting string and the path as second argument
    assert len(fake.logger.warning_calls) >= 1
    first_call = fake.logger.warning_calls[0]
    # The code uses: logger.warning("Found empty trajectory: %s. Removing.", log_path)
    assert first_call[0].startswith("Found empty trajectory")
    # The second positional arg should be the Path
    assert isinstance(first_call[1], Path)
    assert str(first_call[1]).endswith("prob_empty/prob_empty.traj")


def test_should_skip_invalid_json_logs_error_and_removes(tmp_path):
    fake = make_fake_self(tmp_path, redo_existing=False)
    inst = DummyInstance("prob_badjson")
    p = write_traj_file(tmp_path, "prob_badjson", "not a json")
    assert p.exists()
    result = RunBatch.should_skip(fake, inst)
    assert result is False
    # File removed
    assert not p.exists()
    # Error should be logged
    assert len(fake.logger.error_calls) == 1
    err_msg = fake.logger.error_calls[0][0]
    assert "Failed to check existing trajectory" in err_msg
    assert "Removing." in err_msg


def test_should_skip_early_exit_removes_and_logs(tmp_path):
    fake = make_fake_self(tmp_path, redo_existing=False)
    inst = DummyInstance("prob_early")
    content = {"info": {"exit_status": "early_exit"}}
    p = write_traj_file(tmp_path, "prob_early", json.dumps(content))
    assert p.exists()
    result = RunBatch.should_skip(fake, inst)
    assert result is False
    # File removed
    assert not p.exists()
    # Warning should have been called with the formatted message (single arg)
    assert len(fake.logger.warning_calls) >= 1
    # The last warning call should include the formatted message about no exit status and removal
    # The code uses an f-string, so it's a single string argument
    any_msg = None
    for call in fake.logger.warning_calls:
        if isinstance(call[0], str) and "no exit status" in call[0]:
            any_msg = call[0]
            break
    assert any_msg is not None
    assert "Removing." in any_msg


def test_should_skip_existing_valid_exit_status_skips_and_returns_status(tmp_path):
    fake = make_fake_self(tmp_path, redo_existing=False)
    inst = DummyInstance("prob_done")
    content = {"info": {"exit_status": "done"}}
    p = write_traj_file(tmp_path, "prob_done", json.dumps(content))
    assert p.exists()
    result = RunBatch.should_skip(fake, inst)
    # Should return the exit status from the file
    assert result == "done"
    # File should remain because we're skipping (not removing)
    assert p.exists()
    # Info log should have been called indicating skipping
    assert len(fake.logger.info_calls) == 1
    info_msg = fake.logger.info_calls[0][0]
    assert "Skipping existing trajectory" in info_msg or "⏭️ Skipping existing trajectory" in info_msg
