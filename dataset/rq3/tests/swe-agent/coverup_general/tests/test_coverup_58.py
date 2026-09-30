# file: sweagent/run/inspector_cli.py:475-487
# asked: {"lines": [475, 476, 477, 478, 479, 480, 481, 483, 484, 486, 487], "branches": []}
# gained: {"lines": [475, 476, 477, 478, 479, 480, 481, 483, 484, 486, 487], "branches": []}

import os
from pathlib import Path
import importlib

import pytest


@pytest.fixture(autouse=True)
def reload_module():
    # Ensure a fresh import for each test to avoid state leakage between tests.
    module_name = "sweagent.run.inspector_cli"
    if module_name in importlib.sys.modules:
        del importlib.sys.modules[module_name]
    yield
    if module_name in importlib.sys.modules:
        del importlib.sys.modules[module_name]


def test_main_with_no_args(monkeypatch):
    inspector_cli = importlib.import_module("sweagent.run.inspector_cli")

    calls = []

    class DummyApp:
        def __init__(self, trajectory_path):
            # capture the exact value passed in
            calls.append(("init", trajectory_path))

        def run(self):
            calls.append(("run", None))

    monkeypatch.setattr(inspector_cli, "TrajectoryInspectorApp", DummyApp)

    # Call main with empty list so argparse uses the positional default (os.getcwd())
    inspector_cli.main([])

    assert len(calls) == 2
    assert calls[0][0] == "init"
    # trajectory_path default should be os.getcwd()
    assert calls[0][1] == os.getcwd()
    assert calls[1] == ("run", None)


def test_main_with_trajectory_argument(monkeypatch):
    inspector_cli = importlib.import_module("sweagent.run.inspector_cli")

    calls = []

    class DummyApp:
        def __init__(self, trajectory_path):
            calls.append(("init", trajectory_path))

        def run(self):
            calls.append(("run", None))

    monkeypatch.setattr(inspector_cli, "TrajectoryInspectorApp", DummyApp)

    inspector_cli.main(["/some/specific/trajectory.json"])

    assert len(calls) == 2
    assert calls[0] == ("init", "/some/specific/trajectory.json")
    assert calls[1] == ("run", None)


def test_main_with_data_path_flag(monkeypatch, tmp_path):
    inspector_cli = importlib.import_module("sweagent.run.inspector_cli")

    calls = []

    class DummyApp:
        def __init__(self, trajectory_path):
            calls.append(("init", trajectory_path))

        def run(self):
            calls.append(("run", None))

    monkeypatch.setattr(inspector_cli, "TrajectoryInspectorApp", DummyApp)

    data_file = tmp_path / "datafile.json"
    data_file.write_text("{}")

    # Provide the -d/--data_path flag plus a trajectory path; the function does not use data_path,
    # but parsing must accept it and not error.
    inspector_cli.main(["-d", str(data_file), "traj/path.json"])

    assert len(calls) == 2
    assert calls[0] == ("init", "traj/path.json")
    assert calls[1] == ("run", None)
