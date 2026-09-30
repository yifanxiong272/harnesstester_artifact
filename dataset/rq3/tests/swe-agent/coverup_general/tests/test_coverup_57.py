# file: sweagent/run/extract_pred.py:8-19
# asked: {"lines": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19], "branches": []}
# gained: {"lines": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19], "branches": []}

import json
from pathlib import Path

import pytest


def _write_traj(tmp_path: Path, model_name: str, instance_name: str, submission):
    model_dir = tmp_path / model_name
    instance_dir = model_dir / instance_name
    instance_dir.mkdir(parents=True, exist_ok=True)
    traj = instance_dir / "traj.json"
    traj.write_text(json.dumps({"info": {"submission": submission}}))
    return traj, model_dir, instance_dir


def test_run_from_cli_writes_pred_with_dict_submission(tmp_path):
    traj, model_dir, instance_dir = _write_traj(tmp_path, "modelA", "instance1", {"patch": "abc"})

    from sweagent.run.extract_pred import run_from_cli

    # Call the CLI function with the path to the traj file
    run_from_cli([str(traj)])

    pred = traj.with_suffix(".pred")
    assert pred.exists(), "Pred file was not created"
    pred_data = json.loads(pred.read_text())

    # Verify fields were written correctly
    assert pred_data["model_name_or_path"] == model_dir.name
    assert pred_data["instance_id"] == instance_dir.name
    assert pred_data["model_patch"] == {"patch": "abc"}


def test_run_from_cli_writes_pred_with_string_submission(tmp_path):
    traj, model_dir, instance_dir = _write_traj(tmp_path, "modelB", "instance2", "a-string-submission")

    from sweagent.run.extract_pred import run_from_cli

    run_from_cli([str(traj)])

    pred = traj.with_suffix(".pred")
    assert pred.exists()
    pred_data = json.loads(pred.read_text())

    assert pred_data == {
        "model_name_or_path": model_dir.name,
        "model_patch": "a-string-submission",
        "instance_id": instance_dir.name,
    }
