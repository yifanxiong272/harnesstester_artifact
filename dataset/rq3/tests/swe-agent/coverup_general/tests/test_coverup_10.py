# file: sweagent/run/inspector_cli.py:382-409
# asked: {"lines": [382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 401, 403, 405, 406, 407, 408, 409], "branches": [[385, 386], [385, 387], [387, 388], [387, 397], [389, 390], [389, 391], [391, 392], [391, 394], [405, 0], [405, 406]]}
# gained: {"lines": [382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 394, 395, 397, 398, 399, 401, 403, 405, 406, 407, 408, 409], "branches": [[385, 386], [385, 387], [387, 388], [387, 397], [389, 390], [389, 391], [391, 392], [391, 394], [405, 0], [405, 406]]}

import json
import collections
from pathlib import Path

import pytest

from sweagent.run.inspector_cli import TrajectoryInspectorApp


def _write_traj(path: Path, info: dict):
    content = {"info": info}
    path.write_text(json.dumps(content))


def _write_results(path: Path, resolved_ids: list[str]):
    path.write_text(json.dumps({"resolved_ids": resolved_ids}))


def _make_app_instance(tmp_path: Path, traj_names: list[str]):
    """
    Create a TrajectoryInspectorApp instance without running its __init__,
    and set up the minimal attributes required by _build_overview_stats.
    """
    app = TrajectoryInspectorApp.__new__(TrajectoryInspectorApp)
    app.input_path = tmp_path
    # create traj files and set available_traj_paths
    traj_paths = []
    for name in traj_names:
        p = tmp_path / name
        traj_paths.append(p)
    app.available_traj_paths = traj_paths
    app.overview_stats = collections.defaultdict(dict)
    return app


def test_build_overview_stats_with_results(tmp_path: Path):
    # Prepare two traj files: a.traj (resolved), b.traj (unresolved)
    a = tmp_path / "a.traj"
    b = tmp_path / "b.traj"

    _write_traj(a, {"exit_status": "0", "model_stats": {"api_calls": 5, "instance_cost": 0.123}})
    # b missing model_stats and exit_status to exercise defaults
    _write_traj(b, {"some_other": True})

    # write results.json marking 'a' as resolved
    results_path = tmp_path / "results.json"
    _write_results(results_path, ["a"])

    app = _make_app_instance(tmp_path, ["a.traj", "b.traj"])

    # Run the method under test
    app._build_overview_stats()

    # Assertions for results symbols
    assert app.overview_stats["a"]["result"] == "✅"
    assert app.overview_stats["b"]["result"] == "❌"

    # Assertions for info propagated from traj files
    assert app.overview_stats["a"]["info"]["exit_status"] == "0"
    assert app.overview_stats["a"]["exit_status"] == "0"
    assert app.overview_stats["a"]["api_calls"] == 5
    # floating point equality
    assert abs(app.overview_stats["a"]["cost"] - 0.123) < 1e-12

    # For 'b', defaults should be applied
    assert app.overview_stats["b"]["exit_status"] == "?"
    assert app.overview_stats["b"]["api_calls"] == 0
    assert app.overview_stats["b"]["cost"] == 0


def test_build_overview_stats_without_results(tmp_path: Path):
    # Prepare one traj file; no results.json present
    x = tmp_path / "x.traj"
    _write_traj(x, {"exit_status": "1", "model_stats": {"api_calls": 2}})

    app = _make_app_instance(tmp_path, ["x.traj"])

    # Run the method under test
    app._build_overview_stats()

    # When results.json missing, result should be '❓'
    assert app.overview_stats["x"]["result"] == "❓"

    # Info still populated
    assert app.overview_stats["x"]["info"]["exit_status"] == "1"
    assert app.overview_stats["x"]["exit_status"] == "1"
    assert app.overview_stats["x"]["api_calls"] == 2
    # cost default when missing
    assert app.overview_stats["x"]["cost"] == 0
