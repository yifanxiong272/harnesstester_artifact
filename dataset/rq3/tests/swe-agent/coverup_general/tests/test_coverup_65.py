# file: sweagent/run/hooks/apply_patch.py:93-106
# asked: {"lines": [96, 97, 100, 101, 102, 103, 104, 105, 106], "branches": []}
# gained: {"lines": [96, 97, 100, 101, 102, 103, 104, 105, 106], "branches": []}

import subprocess
from pathlib import Path
import pytest

from sweagent.run.hooks.apply_patch import SaveApplyPatchHook


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def _make_instance():
    # Create instance without running __init__
    inst = object.__new__(SaveApplyPatchHook)
    inst.logger = DummyLogger()
    return inst


def test_apply_patch_success(tmp_path, monkeypatch):
    local_dir = tmp_path / "repo"
    local_dir.mkdir()
    patch_file = tmp_path / "fix.diff"
    patch_file.write_text("dummy patch")

    inst = _make_instance()

    called = {}

    def fake_run(cmd, cwd=None, check=False):
        # verify the exact command and cwd passed
        assert cmd == ["git", "apply", str(patch_file.resolve())]
        assert Path(cwd) == local_dir
        assert check is True
        called['ran'] = True
        # emulate subprocess.CompletedProcess return (not used by code)
        return subprocess.CompletedProcess(cmd, 0)

    # Patch the subprocess.run used by the module
    monkeypatch.setattr(
        "sweagent.run.hooks.apply_patch.subprocess.run",
        fake_run,
    )

    inst._apply_patch(patch_file, local_dir)

    # check that fake_run was executed and info was logged
    assert called.get('ran', False) is True
    assert len(inst.logger.errors) == 0
    assert len(inst.logger.infos) == 1
    assert str(patch_file) in inst.logger.infos[0]
    assert str(local_dir) in inst.logger.infos[0]


def test_apply_patch_failure_logs_error_and_returns(tmp_path, monkeypatch):
    local_dir = tmp_path / "repo2"
    local_dir.mkdir()
    patch_file = tmp_path / "bad.diff"
    patch_file.write_text("bad patch")

    inst = _make_instance()

    def fake_run_raise(cmd, cwd=None, check=False):
        # simulate git apply failing
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output=b"fail")

    monkeypatch.setattr(
        "sweagent.run.hooks.apply_patch.subprocess.run",
        fake_run_raise,
    )

    inst._apply_patch(patch_file, local_dir)

    # ensure error was logged and no info was logged
    assert len(inst.logger.errors) == 1
    assert "Failed to apply patch" in inst.logger.errors[0]
    assert len(inst.logger.infos) == 0
