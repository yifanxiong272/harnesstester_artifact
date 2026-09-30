# file: sweagent/run/hooks/swe_bench_evaluate.py:98-113
# asked: {"lines": [98, 99, 100, 101, 102, 103, 107, 108, 111, 112, 113], "branches": [[111, 112], [111, 113]]}
# gained: {"lines": [98, 99, 100, 101, 102, 103, 107, 108, 111, 112, 113], "branches": [[111, 112]]}

import subprocess
import sys
from pathlib import Path
import types
import pytest

from sweagent.run.hooks.swe_bench_evaluate import SweBenchEvaluate


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg, *args):
        try:
            self.infos.append(msg % args if args else msg)
        except Exception:
            # fallback if args don't match format
            self.infos.append(msg)

    def error(self, msg, *args):
        try:
            self.errors.append(msg % args if args else msg)
        except Exception:
            self.errors.append(msg)


def make_instance(tmp_path: Path):
    """
    Create an instance of SweBenchEvaluate without running its constructor,
    and set the attributes used by on_end.
    """
    inst = object.__new__(SweBenchEvaluate)
    inst.logger = DummyLogger()
    inst.output_dir = tmp_path
    # default _get_sb_call that records the preds_path and returns a harmless command
    inst._get_sb_call_calls = []
    def _get_sb_call(preds_path):
        inst._get_sb_call_calls.append(preds_path)
        # return something subprocess.run can accept; actual subprocess.run is monkeypatched in tests
        return ["echo", "ok"]
    inst._get_sb_call = _get_sb_call
    inst.move_called = False
    def move_sb_cli_report():
        inst.move_called = True
    inst.move_sb_cli_report = move_sb_cli_report
    return inst


def test_on_end_subprocess_raises_logs_error(tmp_path, monkeypatch):
    """
    When subprocess.run raises CalledProcessError, on_end should log an error
    and not call move_sb_cli_report nor remove tmppreds.json (even if present).
    """
    inst = make_instance(tmp_path)
    # create tmppreds.json to ensure it would exist
    tmppreds = tmp_path / "tmppreds.json"
    tmppreds.write_text("temporary predictions")

    # Monkeypatch subprocess.run to raise CalledProcessError
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=2, cmd=args[0])
    monkeypatch.setattr(
        "sweagent.run.hooks.swe_bench_evaluate.subprocess.run", fake_run
    )

    # Call on_end
    inst.on_end()

    # Assertions
    # 1) Error logged once and contains expected text
    assert len(inst.logger.errors) == 1
    assert "Failed to submit results to SweBench eval" in inst.logger.errors[0]
    # 2) move_sb_cli_report was not called
    assert inst.move_called is False
    # 3) tmppreds.json still exists
    assert tmppreds.exists()
    # 4) _get_sb_call was called with preds.json path
    assert inst._get_sb_call_calls, "Expected _get_sb_call to be called"
    called_path = inst._get_sb_call_calls[0]
    assert called_path == (tmp_path / "preds.json")


def test_on_end_success_removes_tmppreds_and_moves_report(tmp_path, monkeypatch):
    """
    When subprocess.run succeeds, on_end should remove tmppreds.json (if present)
    and call move_sb_cli_report.
    """
    inst = make_instance(tmp_path)
    # create tmppreds.json to ensure it will be removed
    tmppreds = tmp_path / "tmppreds.json"
    tmppreds.write_text("temporary predictions")
    assert tmppreds.exists()

    # Monkeypatch subprocess.run to simulate successful run
    class FakeCompleted:
        returncode = 0
    def fake_run(*args, **kwargs):
        # check that stdout and stderr are forwarded
        assert kwargs.get("stdout") is sys.stdout
        assert kwargs.get("stderr") is sys.stderr
        return FakeCompleted()
    monkeypatch.setattr(
        "sweagent.run.hooks.swe_bench_evaluate.subprocess.run", fake_run
    )

    # Call on_end
    inst.on_end()

    # Assertions
    # 1) No error logged
    assert len(inst.logger.errors) == 0
    # 2) tmppreds.json removed
    assert not tmppreds.exists()
    # 3) move_sb_cli_report called
    assert inst.move_called is True
    # 4) _get_sb_call was called with preds.json path
    assert inst._get_sb_call_calls, "Expected _get_sb_call to be called"
    called_path = inst._get_sb_call_calls[0]
    assert called_path == (tmp_path / "preds.json")
