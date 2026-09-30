# file: sweagent/run/run_traj_to_demo.py:59-65
# asked: {"lines": [59, 60, 61, 62, 63, 64, 65], "branches": [[61, 62], [61, 64]]}
# gained: {"lines": [59, 60, 61, 62, 63, 64, 65], "branches": [[61, 62], [61, 64]]}

import importlib
from pathlib import Path
import pytest


def test_main_raises_if_output_exists(tmp_path):
    mod = importlib.import_module("sweagent.run.run_traj_to_demo")

    # prepare traj path
    traj_parent = tmp_path / "trajparent"
    traj_parent.mkdir()
    traj_path = traj_parent / "sample.traj"
    traj_path.write_text("traj content")

    # compute expected output file and create it to simulate existing output
    output_dir = tmp_path / "outdir"
    expected_output_file = output_dir / (traj_path.parent.name + "") / (traj_path.stem.removesuffix(".traj") + ".demo.yaml")
    expected_output_file.parent.mkdir(parents=True, exist_ok=True)
    expected_output_file.write_text("existing demo")

    # call main and expect FileExistsError when overwrite is False
    with pytest.raises(FileExistsError) as excinfo:
        mod.main(traj_path, output_dir, suffix="", overwrite=False, include_user=False)

    msg = str(excinfo.value)
    assert "Output file already exists" in msg
    assert str(expected_output_file) in msg


def test_main_overwrite_calls_convert(monkeypatch, tmp_path):
    mod = importlib.import_module("sweagent.run.run_traj_to_demo")

    # prepare traj path
    traj_parent = tmp_path / "tp"
    traj_parent.mkdir()
    traj_path = traj_parent / "demo.traj"
    traj_path.write_text("traj content")

    # output file that already exists
    output_dir = tmp_path / "out"
    suffix = "_suf"
    expected_output_file = output_dir / (traj_path.parent.name + suffix) / (traj_path.stem.removesuffix(".traj") + ".demo.yaml")
    expected_output_file.parent.mkdir(parents=True, exist_ok=True)
    expected_output_file.write_text("old demo")

    called = {}

    def fake_convert(traj_arg, out_arg, include_user_arg):
        # record call arguments and simulate writing to output file
        called["args"] = (traj_arg, out_arg, include_user_arg)
        out_arg.write_text("converted content")

    monkeypatch.setattr(mod, "convert_traj_to_action_demo", fake_convert)

    # Call with overwrite=True so the function should not raise and should call our fake_convert
    mod.main(traj_path, output_dir, suffix=suffix, overwrite=True, include_user=True)

    assert "args" in called
    traj_arg, out_arg, include_user_arg = called["args"]
    assert traj_arg == traj_path
    assert out_arg == expected_output_file
    assert include_user_arg is True
    assert expected_output_file.exists()
    assert expected_output_file.read_text() == "converted content"


def test_main_creates_parent_dir_and_calls_convert_when_output_missing(monkeypatch, tmp_path):
    mod = importlib.import_module("sweagent.run.run_traj_to_demo")

    # prepare traj path
    traj_parent = tmp_path / "parentx"
    traj_parent.mkdir()
    traj_path = traj_parent / "file.traj"
    traj_path.write_text("traj")

    output_dir = tmp_path / "outx"
    suffix = ""
    expected_output_file = output_dir / (traj_path.parent.name + suffix) / (traj_path.stem.removesuffix(".traj") + ".demo.yaml")

    # ensure output does not exist
    assert not expected_output_file.exists()
    called = {}

    def fake_convert(traj_arg, out_arg, include_user_arg):
        called["called"] = True
        called["traj"] = traj_arg
        called["out"] = out_arg
        called["include_user"] = include_user_arg
        out_arg.write_text("converted")

    monkeypatch.setattr(mod, "convert_traj_to_action_demo", fake_convert)

    mod.main(traj_path, output_dir, suffix=suffix, overwrite=False, include_user=False)

    # parent directory should have been created and convert called
    assert expected_output_file.parent.exists()
    assert expected_output_file.exists()
    assert expected_output_file.read_text() == "converted"
    assert called.get("called", False) is True
    assert called["traj"] == traj_path
    assert called["out"] == expected_output_file
    assert called["include_user"] is False
