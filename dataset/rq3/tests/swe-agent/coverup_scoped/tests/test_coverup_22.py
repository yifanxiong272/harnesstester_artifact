# file: sweagent/run/run_batch.py:103-117
# asked: {"lines": [107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117], "branches": [[106, 107], [114, 115], [114, 116]]}
# gained: {"lines": [107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117], "branches": [[106, 107], [114, 115], [114, 116]]}

import importlib
from pathlib import Path

import pytest


def _make_dummy(**kwargs):
    class D:
        pass

    d = D()
    for k, v in kwargs.items():
        setattr(d, k, v)
    return d


def test_set_default_output_dir_with_model_and_config_and_suffix(tmp_path, monkeypatch):
    run_batch = importlib.import_module("sweagent.run.run_batch")
    RunBatchConfig = getattr(run_batch, "RunBatchConfig")

    fake_traj = tmp_path / "traj"
    monkeypatch.setattr(run_batch, "TRAJECTORY_DIR", fake_traj)

    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: "alice")

    # Use pydantic's construct to avoid validation/initialization issues
    rc = RunBatchConfig.construct()
    rc.output_dir = Path("DEFAULT")
    rc.instances = _make_dummy(id="source123")
    rc.agent = _make_dummy(model=_make_dummy(id="modelX"))
    rc.suffix = "sfx"
    rc._config_files = ["/home/user/configs/foo.yaml"]

    rc.set_default_output_dir()

    expected = fake_traj / "alice" / "foo__modelX___source123__sfx"
    assert rc.output_dir == expected


def test_set_default_output_dir_without_model_and_no_config_no_suffix(tmp_path, monkeypatch):
    run_batch = importlib.import_module("sweagent.run.run_batch")
    RunBatchConfig = getattr(run_batch, "RunBatchConfig")

    fake_traj = tmp_path / "traj2"
    monkeypatch.setattr(run_batch, "TRAJECTORY_DIR", fake_traj)

    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: "bob")

    rc = RunBatchConfig.construct()
    rc.output_dir = Path("DEFAULT")
    rc.instances = _make_dummy(id="src")
    # Agent without a 'model' attribute to trigger AttributeError branch
    rc.agent = _make_dummy()
    rc.suffix = ""  # no suffix
    # Do not set _config_files so getattr falls back to ["no_config"]

    rc.set_default_output_dir()

    expected = fake_traj / "bob" / "no_config__unknown___src"
    assert rc.output_dir == expected
