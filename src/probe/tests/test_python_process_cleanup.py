"""Independent lifecycle regressions, including real POSIX descendants."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

import pytest

from probe.python.runtime import validate


def running(pid):
    state = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return bool(state) and not state.startswith("Z")


def wait_until_stopped(pid):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            if not running(pid):
                return
        except subprocess.CalledProcessError as exc:
            if exc.returncode == 1:
                return
            raise
        time.sleep(0.01)
    pytest.fail(f"process {pid} still running")


@pytest.fixture
def processes(monkeypatch):
    """Keep a test-owned cleanup path even if the production assertion fails."""
    if os.name != "posix":
        pytest.skip("real process-group checks require POSIX")
    created = []
    popen = subprocess.Popen

    def track(*args, **kwargs):
        proc = popen(*args, **kwargs)
        created.append(proc)
        return proc

    monkeypatch.setattr(validate.subprocess, "Popen", track)
    yield created
    for proc in created:
        # Only run_command starts a new session; ps belongs to the test runner.
        if proc.args[0] == "ps":
            continue
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=3)
        if proc.stdout is not None:
            proc.stdout.close()


@pytest.mark.parametrize("mode", ["normal", "invalid_output", "timeout"])
def test_real_term_ignoring_descendant_is_cleaned(tmp_path, processes, mode):
    ready = tmp_path / "child.json"
    child = "\n".join([
        "import json, os, signal, sys, time",
        "from pathlib import Path",
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)",
        "Path(sys.argv[1]).write_text(json.dumps([os.getpid(), os.getpgrp()]))",
        "time.sleep(20)",
    ])
    parent = "\n".join([
        "import os, subprocess, sys, time",
        "from pathlib import Path",
        f"subprocess.Popen([sys.executable, '-c', {child!r}, {str(ready)!r}], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)",
        "deadline = time.monotonic() + 3",
        f"while not Path({str(ready)!r}).exists() and time.monotonic() < deadline: time.sleep(0.01)",
        "print('parent ready', flush=True)",
        "os.write(1, b'\\xff')" if mode == "invalid_output" else "pass",
        "time.sleep(20)" if mode == "timeout" else "pass",
    ])
    started = time.monotonic()
    try:
        if mode == "invalid_output":
            with pytest.raises(UnicodeDecodeError):
                validate.run_command([sys.executable, "-c", parent], cwd=tmp_path, timeout=5)
        else:
            result = validate.run_command(
                [sys.executable, "-c", parent], cwd=tmp_path,
                timeout=1 if mode == "timeout" else 5,
            )
            assert result["timed_out"] is (mode == "timeout")
            assert result["exit_code"] == (None if mode == "timeout" else 0)
            assert "parent ready" in result["output_tail"]
            assert result["process_group_cleanup"] == {"attempted": True, "signal": "SIGKILL"}
        assert time.monotonic() - started < 5
        pid, pgid = json.loads(ready.read_text())
        assert pgid == processes[0].pid
        wait_until_stopped(pid)
        assert processes[0].poll() is not None
        assert processes[0].stdout.closed
    finally:
        if ready.exists():
            pid, pgid = json.loads(ready.read_text())
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            wait_until_stopped(pid)


@pytest.mark.parametrize("error_type", [OSError, KeyboardInterrupt, RuntimeError])
def test_real_process_read_failure_preserves_error_and_cleans(
    tmp_path, monkeypatch, processes, error_type,
):
    popen = validate.subprocess.Popen
    error = error_type("fixture read failure")

    def start(*args, **kwargs):
        proc = popen(*args, **kwargs)

        def fail(**kwargs):
            raise error

        monkeypatch.setattr(proc, "communicate", fail)
        return proc

    monkeypatch.setattr(validate.subprocess, "Popen", start)
    with pytest.raises(error_type) as caught:
        validate.run_command(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            cwd=tmp_path, timeout=2,
        )
    assert caught.value is error
    assert processes[0].poll() is not None
    assert processes[0].stdout.closed


@pytest.mark.parametrize("error_type", [OSError, UnicodeError, KeyboardInterrupt])
def test_cleanup_failure_does_not_mask_original_error(tmp_path, monkeypatch, error_type):
    from io import StringIO
    from types import SimpleNamespace

    original = error_type("original read failure")

    def fail(**kwargs):
        raise original

    proc = SimpleNamespace(communicate=fail, stdout=StringIO())
    monkeypatch.setattr(validate.subprocess, "Popen", lambda *args, **kwargs: proc)

    def cleanup(*args, **kwargs):
        raise OSError("cleanup failed")

    monkeypatch.setattr(validate, "terminate_process_group", cleanup)
    with pytest.raises(error_type) as caught:
        validate.run_command(["fixture"], cwd=tmp_path)
    assert caught.value is original
    assert proc.stdout.closed


def test_cleanup_failure_after_success_is_not_hidden(tmp_path, monkeypatch):
    from io import StringIO
    from types import SimpleNamespace

    proc = SimpleNamespace(communicate=lambda **kwargs: ("done", None), returncode=0, stdout=StringIO())
    monkeypatch.setattr(validate.subprocess, "Popen", lambda *args, **kwargs: proc)
    error = OSError("cleanup failed")

    def cleanup(*args, **kwargs):
        raise error

    monkeypatch.setattr(validate, "terminate_process_group", cleanup)
    with pytest.raises(OSError) as caught:
        validate.run_command(["fixture"], cwd=tmp_path)
    assert caught.value is error
    assert proc.stdout.closed


def test_timeout_drain_is_bounded_and_closes_pipe(tmp_path, monkeypatch):
    from io import StringIO
    from types import SimpleNamespace

    timeouts = []

    def communicate(timeout):
        timeouts.append(timeout)
        raise subprocess.TimeoutExpired(["fixture"], timeout)

    proc = SimpleNamespace(communicate=communicate, stdout=StringIO())
    monkeypatch.setattr(validate.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(validate, "terminate_process_group", lambda *args, **kwargs: {"attempted": True})
    with pytest.raises(subprocess.TimeoutExpired):
        validate.run_command(["fixture"], cwd=tmp_path, timeout=2)
    assert timeouts == [2, 1]
    assert proc.stdout.closed


def test_expired_budget_does_not_start_process(tmp_path, monkeypatch):
    error = validate.CaseTimeBudgetExceeded("expired before launch")

    def limit(*args):
        raise error

    monkeypatch.setattr(validate, "limit_timeout", limit)
    monkeypatch.setattr(
        validate.subprocess, "Popen",
        lambda *args, **kwargs: pytest.fail("expired budget launched a process"),
    )
    with pytest.raises(validate.CaseTimeBudgetExceeded) as caught:
        validate.run_command(["fixture"], cwd=tmp_path)
    assert caught.value is error
