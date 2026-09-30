# file: sweagent/inspector/server.py:51-120
# asked: {"lines": [51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 63, 64, 65, 66, 67, 68, 70, 71, 72, 73, 74, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 91, 94, 96, 97, 99, 100, 101, 103, 104, 105, 108, 109, 110, 111, 112, 113, 116, 117, 118, 119, 120], "branches": [[54, 55], [54, 60], [79, 80], [79, 81], [81, 82], [81, 94], [96, 97], [96, 99], [116, 117], [116, 118]]}
# gained: {"lines": [51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 63, 64, 65, 66, 67, 68, 70, 71, 72, 73, 74, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 91, 94, 96, 99, 100, 101, 103, 104, 105, 108, 109, 110, 111, 112, 113, 116, 117, 118, 119, 120], "branches": [[54, 55], [79, 80], [79, 81], [81, 82], [81, 94], [96, 99], [116, 117], [116, 118]]}

import json
from pathlib import Path

import pytest

from sweagent.inspector.server import append_results


def test_append_results_no_traj_file(tmp_path):
    traj_path = tmp_path / "no_traj.json"
    # Create an empty JSON file so that `info` is defined in the function (avoids UnboundLocalError)
    traj_path.write_text(json.dumps({}))

    instance_id = "inst_no_file"
    content = {}
    results = None
    results_file = "results.json"

    out = append_results(traj_path, instance_id, content, results, results_file)

    # Check trajectory was created and has two identical eval reports
    assert "trajectory" in out
    assert isinstance(out["trajectory"], list)
    assert len(out["trajectory"]) == 2

    first = out["trajectory"][0]
    last = out["trajectory"][-1]

    # They should be equal in content
    assert first == last

    obs = first["observation"]
    # Since traj file contains empty info, exit_status should be N/A and stats should be N/A
    assert "Exit Status: N/A" in obs
    assert "Instance Cost: $N/A" in obs
    assert "Tokens Sent: N/A" in obs
    assert "Tokens Received: N/A" in obs
    assert "API Calls: N/A" in obs

    # Results was None so it should say evaluation results not found and include results_file in footer
    assert "Evaluation results not found" in obs
    assert f"Check {results_file} for the most accurate evaluation results." in obs
    assert f"Instance ID: {instance_id}" in obs

    # Messages and other keys present
    assert first["thought"] == "Evaluation Report"
    assert any(m.get("role") == "system" for m in first.get("messages", []))


def test_append_results_with_traj_and_stats(tmp_path):
    # Create a trajectory file with info and model_stats
    traj_path = tmp_path / "traj.json"
    data = {
        "info": {
            "exit_status": "Completed",
            "model_stats": {
                "instance_cost": 1.2345,
                "tokens_sent": 1234,
                "tokens_received": 5678,
                "api_calls": 9,
            },
        }
    }
    traj_path.write_text(json.dumps(data))

    instance_id = "instance123"
    # content already has one trajectory item to ensure insert/append behavior
    content = {"trajectory": [{"thought": "old_entry"}]}
    results = {
        "completed_ids": [instance_id],
        "submitted_ids": [instance_id],
        "resolved_ids": [instance_id],
    }
    results_file = "eval_results.json"

    out = append_results(traj_path, instance_id, content, results, results_file)

    # Now trajectory should have original item in the middle, and two eval reports added
    assert "trajectory" in out
    traj = out["trajectory"]
    assert len(traj) == 3
    assert traj[1]["thought"] == "old_entry"

    first_report = traj[0]
    last_report = traj[-1]

    # Reports should be equal
    assert first_report == last_report

    obs = first_report["observation"]

    # Check that numeric formatting is applied
    assert "Exit Status: Completed" in obs
    # instance_cost formatted to 2 decimals
    assert "Instance Cost: $1.23" in obs
    # tokens with thousands separator
    assert "Tokens Sent: 1,234" in obs
    assert "Tokens Received: 5,678" in obs
    # api_calls formatted without commas
    assert "API Calls: 9" in obs

    # All statuses should be check marks (✅)
    assert "✅ Completed" in obs
    assert "✅ Submitted" in obs
    assert "✅ Resolved" in obs

    # Footer should include results_file and instance id
    assert f"Check {results_file} for the most accurate evaluation results." in obs
    assert f"Instance ID: {instance_id}" in obs


def test_append_results_with_unrecognized_results_format(tmp_path):
    traj_path = tmp_path / "missing2.json"
    # Create an empty JSON file so that `info` exists
    traj_path.write_text(json.dumps({}))

    instance_id = "unknown_inst"
    content = {}
    # results present but wrong format (missing expected keys)
    results = {"unexpected": "value"}
    results_file = "some_results_file.txt"

    out = append_results(traj_path, instance_id, content, results, results_file)

    assert "trajectory" in out
    assert len(out["trajectory"]) == 2
    report = out["trajectory"][0]
    obs = report["observation"]

    # Should indicate that results format was not recognized
    assert "Results format not recognized" in obs

    # Footer should still be present with results_file and instance id
    assert f"Check {results_file} for the most accurate evaluation results." in obs
    assert f"Instance ID: {instance_id}" in obs
