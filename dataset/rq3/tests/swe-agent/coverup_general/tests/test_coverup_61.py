# file: sweagent/run/inspector_cli.py:427-432
# asked: {"lines": [427, 428, 429, 430, 431, 432], "branches": [[428, 429], [428, 430], [430, 431], [430, 432]]}
# gained: {"lines": [427, 428, 429, 430, 431, 432], "branches": [[428, 429], [428, 430], [430, 431], [430, 432]]}

import pytest
from pathlib import Path
from sweagent.run.inspector_cli import TrajectoryInspectorApp

def test_get_available_trajs_file(tmp_path: Path):
    # create a .traj file
    traj_file = tmp_path / "single.traj"
    traj_file.write_text("dummy")
    # create a bare instance without running __init__
    inst = object.__new__(TrajectoryInspectorApp)
    inst.input_path = traj_file
    res = TrajectoryInspectorApp._get_available_trajs(inst)
    assert isinstance(res, list)
    assert res == [traj_file]

def test_get_available_trajs_dir_with_multiple_traj_files(tmp_path: Path):
    # create directory structure with .traj files
    d = tmp_path / "trajs"
    d.mkdir()
    (d / "b.traj").write_text("b")
    sub = d / "sub"
    sub.mkdir()
    (sub / "a.traj").write_text("a")
    # add a non-traj file to ensure rglob filters correctly
    (d / "ignore.txt").write_text("nope")

    inst = object.__new__(TrajectoryInspectorApp)
    inst.input_path = d
    res = TrajectoryInspectorApp._get_available_trajs(inst)

    expected = sorted(list(d.rglob("*.traj")))
    assert res == expected
    # ensure both created traj files are present and the non-traj is not
    assert any(p.name == "a.traj" for p in res)
    assert any(p.name == "b.traj" for p in res)
    assert all(p.suffix == ".traj" for p in res)

def test_get_available_trajs_neither_file_nor_dir(tmp_path: Path):
    # path does not exist -> neither file nor dir
    missing = tmp_path / "does_not_exist"
    inst = object.__new__(TrajectoryInspectorApp)
    inst.input_path = missing
    with pytest.raises(ValueError):
        TrajectoryInspectorApp._get_available_trajs(inst)
