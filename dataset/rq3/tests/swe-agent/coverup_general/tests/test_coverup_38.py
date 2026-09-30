# file: sweagent/inspector/server.py:180-193
# asked: {"lines": [180, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 193], "branches": [[188, 189], [188, 190], [190, 191], [190, 193]]}
# gained: {"lines": [180, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 193], "branches": [[188, 189], [188, 190], [190, 191], [190, 193]]}

import json
from pathlib import Path

import pytest

import sweagent.inspector.server as server


def _write_traj_file(path: Path, info: dict):
    path.write_text(json.dumps({"info": info}))


def test_get_status_results_none(tmp_path, monkeypatch):
    # Create a trajectory file with known info
    traj = tmp_path / "traj_none.json"
    info = {"model_stats": {"api_calls": 5}, "exit_status": "crashed"}
    _write_traj_file(traj, info)

    # Monkeypatch load_results to simulate missing results (None)
    monkeypatch.setattr(server, "load_results", lambda p: None)

    res = server.get_status(traj)
    # It should indicate unknown results with the exit_status and step count included
    assert res.startswith("❓")
    assert "crashed" in res
    assert "after 5 steps" in res


def test_get_status_resolved_id(tmp_path, monkeypatch):
    # Create a trajectory file whose stem will be considered the instance id
    traj = tmp_path / "instance_42.json"
    # minimal info is fine; resolved case should return plain checkmark
    _write_traj_file(traj, {})  # info will default to {}

    # Monkeypatch load_results to include the instance id in resolved_ids
    monkeypatch.setattr(server, "load_results", lambda p: {"resolved_ids": ["instance_42"]})

    res = server.get_status(traj)
    assert res == "✅"


def test_get_status_unresolved_id(tmp_path, monkeypatch):
    # Create trajectory file with explicit info
    traj = tmp_path / "unresolved_id.json"
    info = {"model_stats": {"api_calls": 10}, "exit_status": "finished"}
    _write_traj_file(traj, info)

    # Monkeypatch load_results to return a results dict that does NOT contain this id
    monkeypatch.setattr(server, "load_results", lambda p: {"resolved_ids": ["other_id"]})

    res = server.get_status(traj)
    # Should indicate failure with exit status and step count
    assert res.startswith("❌")
    assert "finished" in res
    assert "after 10 steps" in res
