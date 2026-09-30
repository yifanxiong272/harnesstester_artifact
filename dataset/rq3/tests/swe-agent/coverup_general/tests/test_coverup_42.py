# file: sweagent/run/hooks/apply_patch.py:32-45
# asked: {"lines": [38, 39, 40, 41, 42, 43, 44, 45], "branches": [[36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 44]]}
# gained: {"lines": [38, 39, 40, 41, 42, 43, 44, 45], "branches": [[36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 44]]}

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
import sweagent.run.common as run_common
from sweagent.environment.repo import LocalRepoConfig


def make_result(info):
    # simple object with .info attribute
    return SimpleNamespace(info=info)


def test_returns_when_not_promising_patch(monkeypatch):
    hook = SaveApplyPatchHook(apply_patch_locally=True)
    # ensure problem statement id exists
    hook._problem_statement = SimpleNamespace(id="inst-1")
    # make _save_patch return a Path so the branch is entered
    saved = Path(tempfile.gettempdir()) / "patch.diff"
    monkeypatch.setattr(hook, "_save_patch", lambda instance_id, info: saved)
    # ensure _apply_patch would fail if called
    called = {"count": 0}

    def fail_apply(patch_file, local_dir):
        called["count"] += 1

    monkeypatch.setattr(hook, "_apply_patch", fail_apply)
    # make _is_promising_patch return False to trigger the early return at line 39
    monkeypatch.setattr(run_common, "_is_promising_patch", lambda info: False)

    result = make_result({"some": "info"})
    hook._env = SimpleNamespace(repo="irrelevant")
    hook.on_instance_completed(result=result)

    assert called["count"] == 0


def test_returns_when_repo_is_none(monkeypatch):
    hook = SaveApplyPatchHook(apply_patch_locally=True)
    hook._problem_statement = SimpleNamespace(id="inst-2")
    saved = Path(tempfile.gettempdir()) / "patch2.diff"
    monkeypatch.setattr(hook, "_save_patch", lambda instance_id, info: saved)

    called = {"count": 0}

    def fail_apply(patch_file, local_dir):
        called["count"] += 1

    monkeypatch.setattr(hook, "_apply_patch", fail_apply)
    # promising
    monkeypatch.setattr(run_common, "_is_promising_patch", lambda info: True)

    # env.repo is None -> should return early at lines 40-41
    hook._env = SimpleNamespace(repo=None)
    result = make_result({"exit_status": "submitted", "submission": "x"})
    hook.on_instance_completed(result=result)

    assert called["count"] == 0


def test_returns_when_repo_not_local(monkeypatch):
    hook = SaveApplyPatchHook(apply_patch_locally=True)
    hook._problem_statement = SimpleNamespace(id="inst-3")
    saved = Path(tempfile.gettempdir()) / "patch3.diff"
    monkeypatch.setattr(hook, "_save_patch", lambda instance_id, info: saved)

    called = {"count": 0}

    def fail_apply(patch_file, local_dir):
        called["count"] += 1

    monkeypatch.setattr(hook, "_apply_patch", fail_apply)
    # promising
    monkeypatch.setattr(run_common, "_is_promising_patch", lambda info: True)

    # env.repo exists but is not LocalRepoConfig -> should return at lines 42-43
    hook._env = SimpleNamespace(repo={"path": "/tmp"})
    result = make_result({"exit_status": "submitted", "submission": "x"})
    hook.on_instance_completed(result=result)

    assert called["count"] == 0


def test_applies_patch_when_all_conditions_met(monkeypatch, tmp_path):
    hook = SaveApplyPatchHook(apply_patch_locally=True)
    hook._problem_statement = SimpleNamespace(id="inst-4")
    saved = tmp_path / "patch4.diff"
    # create dummy file to mimic saved patch (not strictly necessary but realistic)
    saved.write_text("diff --git a/file b/file\n")
    monkeypatch.setattr(hook, "_save_patch", lambda instance_id, info: saved)

    called = {"args": None}

    def record_apply(patch_file, local_dir):
        called["args"] = (patch_file, local_dir)

    monkeypatch.setattr(hook, "_apply_patch", record_apply)
    # promising
    monkeypatch.setattr(run_common, "_is_promising_patch", lambda info: True)

    # env.repo is a LocalRepoConfig with path pointing to tmp_path
    hook._env = SimpleNamespace(repo=LocalRepoConfig(path=tmp_path))
    result = make_result({"exit_status": "submitted", "submission": "x"})
    hook.on_instance_completed(result=result)

    assert called["args"] is not None
    patch_file_arg, local_dir_arg = called["args"]
    assert Path(patch_file_arg) == saved
    assert Path(local_dir_arg) == tmp_path
