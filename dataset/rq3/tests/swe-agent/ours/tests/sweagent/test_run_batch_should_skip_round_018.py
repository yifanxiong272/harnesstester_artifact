import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from sweagent.run.run_batch import RunBatch


class DummyLogger:
    def __init__(self, store):
        self.store = store

    def warning(self, msg, *args):
        # support both %-format calls and direct string messages
        if args:
            try:
                formatted = msg % args
            except Exception:
                formatted = str(msg) + " " + " ".join(map(str, args))
        else:
            formatted = msg
        self.store.append(("warning", str(formatted)))

    def info(self, msg, *args):
        if args:
            try:
                formatted = msg % args
            except Exception:
                formatted = str(msg) + " " + " ".join(map(str, args))
        else:
            formatted = msg
        self.store.append(("info", str(formatted)))

    def error(self, msg, *args):
        if args:
            try:
                formatted = msg % args
            except Exception:
                formatted = str(msg) + " " + " ".join(map(str, args))
        else:
            formatted = msg
        self.store.append(("error", str(formatted)))


class DummySelf:
    def __init__(self, output_dir, redo=False):
        self._redo_existing = redo
        self.output_dir = Path(output_dir)
        self.logged = []
        self.logger = DummyLogger(self.logged)


def make_instance(id_: str):
    return SimpleNamespace(problem_statement=SimpleNamespace(id=id_))


def call_should_skip(self_obj, instance):
    # call the unbound function from the class to exercise the real implementation
    fn = RunBatch.should_skip
    return fn(self_obj, instance)


def test_should_skip_redo_flag_round_018(tmp_path):
    # If redo_existing is True, should return False immediately and not touch files
    out = tmp_path
    traj_dir = out / "probA"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probA.traj"
    traj_file.write_text('{"info": {"exit_status": "success"}}')

    s = DummySelf(out, redo=True)
    inst = make_instance("probA")

    res = call_should_skip(s, inst)
    assert res is False
    # file must remain untouched because function returns early
    assert traj_file.exists()
    # no warnings/errors/info should have been recorded by our logger
    assert s.logged == []


def test_should_skip_no_log_path_round_018(tmp_path):
    # When trajectory file does not exist, should return False
    out = tmp_path
    s = DummySelf(out, redo=False)
    inst = make_instance("missing")

    res = call_should_skip(s, inst)
    assert res is False
    # Ensure no log entries were created for this simple negative case
    assert s.logged == []


def test_should_skip_empty_content_round_018(tmp_path):
    # Empty or whitespace-only trajectory file should be removed and return False
    out = tmp_path
    traj_dir = out / "probB"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probB.traj"
    traj_file.write_text("   \n   ")

    s = DummySelf(out, redo=False)
    inst = make_instance("probB")

    res = call_should_skip(s, inst)
    assert res is False
    # file should have been unlinked
    assert not traj_file.exists()
    # logger should have recorded a warning mentioning empty trajectory
    assert any("Found empty trajectory" in msg for level, msg in s.logged if level == "warning")


def test_should_skip_invalid_json_round_018(tmp_path):
    # Invalid JSON should hit the exception branch, remove file, and return False
    out = tmp_path
    traj_dir = out / "probC"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probC.traj"
    traj_file.write_text("not a json {oops}")

    s = DummySelf(out, redo=False)
    inst = make_instance("probC")

    res = call_should_skip(s, inst)
    assert res is False
    assert not traj_file.exists()
    # logger should have an error entry indicating failure to check trajectory
    assert any("Failed to check existing trajectory" in msg for level, msg in s.logged if level == "error")


def test_should_skip_missing_exit_status_round_018(tmp_path):
    # JSON with missing exit_status (None) should be treated as incomplete and removed
    out = tmp_path
    traj_dir = out / "probD"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probD.traj"
    traj_file.write_text(json.dumps({"info": {}}))

    s = DummySelf(out, redo=False)
    inst = make_instance("probD")

    res = call_should_skip(s, inst)
    assert res is False
    assert not traj_file.exists()
    # Ensure warning about missing exit status
    assert any("no exit status" in msg for level, msg in s.logged if level == "warning")


def test_should_skip_early_exit_round_018(tmp_path):
    # JSON with exit_status == "early_exit" should be removed and return False
    out = tmp_path
    traj_dir = out / "probE"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probE.traj"
    traj_file.write_text(json.dumps({"info": {"exit_status": "early_exit"}}))

    s = DummySelf(out, redo=False)
    inst = make_instance("probE")

    res = call_should_skip(s, inst)
    assert res is False
    assert not traj_file.exists()
    assert any("no exit status" in msg or "no exit status" in msg.lower() for level, msg in s.logged if level == "warning")


def test_should_skip_skip_existing_round_018(tmp_path):
    # JSON with a concrete exit_status should result in skipping and returning that status
    out = tmp_path
    traj_dir = out / "probF"
    traj_dir.mkdir(parents=True)
    traj_file = traj_dir / "probF.traj"
    traj_file.write_text(json.dumps({"info": {"exit_status": "success"}}))

    s = DummySelf(out, redo=False)
    inst = make_instance("probF")

    res = call_should_skip(s, inst)
    assert res == "success"
    # file should remain in place for successful skip
    assert traj_file.exists()
    # info log about skipping should have been recorded
    assert any("Skipping existing trajectory" in msg for level, msg in s.logged if level == "info")
