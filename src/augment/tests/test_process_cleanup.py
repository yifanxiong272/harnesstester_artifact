"""Bounded validation cleanup, including real POSIX descendants."""

from __future__ import annotations

from io import StringIO
import json
import os
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from augment.python import process
from augment.python.run import validate


def running(pid):
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)],
        capture_output=True, text=True, timeout=2, check=False,
    )
    assert result.returncode in (0, 1)
    state = result.stdout.strip()
    return bool(state) and not state.startswith("Z")


def wait_until_stopped(pid):
    deadline = time.monotonic() + 3
    while running(pid):
        if time.monotonic() >= deadline:
            pytest.fail(f"process {pid} still running")
        time.sleep(0.01)


@pytest.fixture
def processes(monkeypatch):
    if os.name != "posix":
        pytest.skip("real process-group checks require POSIX")
    created = []
    start = validate.start_process

    def track(*args, **kwargs):
        proc = start(*args, **kwargs)
        created.append(proc)
        return proc

    monkeypatch.setattr(validate, "start_process", track)
    try:
        yield created
    finally:
        for proc in created:
            proc.poll()
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                if proc.poll() is None:
                    proc.kill()
            proc.wait(timeout=3)
            if proc.stdout is not None:
                proc.stdout.close()


@pytest.mark.parametrize("mode", ["normal", "nonzero", "decode_error", "interrupt", "timeout"])
def test_real_term_ignoring_descendant_is_cleaned(tmp_path, monkeypatch, processes, mode):
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
        f"subprocess.Popen([sys.executable, '-B', '-c', {child!r}, {str(ready)!r}], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)",
        "deadline = time.monotonic() + 3",
        f"while not Path({str(ready)!r}).exists() and time.monotonic() < deadline: time.sleep(0.01)",
        f"assert Path({str(ready)!r}).exists()",
        "print('parent ready', flush=True)",
        "os.write(1, b'\\xff')" if mode == "decode_error" else "pass",
        "time.sleep(20)" if mode in {"timeout", "interrupt"} else "pass",
        "sys.exit(7)" if mode == "nonzero" else "pass",
    ])
    interrupt = KeyboardInterrupt("controlled read interruption")
    if mode == "interrupt":
        start = validate.start_process

        def interrupted_start(*args, **kwargs):
            proc = start(*args, **kwargs)

            def interrupted_communicate(**kwargs):
                deadline = time.monotonic() + 3
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert ready.exists()
                raise interrupt

            monkeypatch.setattr(proc, "communicate", interrupted_communicate)
            return proc

        monkeypatch.setattr(validate, "start_process", interrupted_start)

    started = time.monotonic()
    try:
        args = ([sys.executable, "-B", "-c", parent],)
        kwargs = {
            "cwd": tmp_path, "timeout": 1 if mode == "timeout" else 5,
            "env": {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            "keep_output": True,
        }
        if mode in {"decode_error", "interrupt"}:
            error_type = UnicodeDecodeError if mode == "decode_error" else KeyboardInterrupt
            with pytest.raises(error_type) as caught:
                validate.run_command(*args, **kwargs)
            if mode == "interrupt":
                assert caught.value is interrupt
        else:
            result = validate.run_command(*args, **kwargs)
            assert result.get("timed_out", False) is (mode == "timeout")
            assert result["exit_code"] == (None if mode == "timeout" else 7 if mode == "nonzero" else 0)
            assert result["output"] == result["output_tail"] == "parent ready\n"
        assert time.monotonic() - started < 5
        pid, pgid = json.loads(ready.read_text())
        assert pgid == processes[0].pid
        wait_until_stopped(pid)
        assert processes[0].poll() is not None
        assert processes[0].stdout.closed
    finally:
        if ready.exists():
            pid, pgid = json.loads(ready.read_text())
            if running(pid):
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    if running(pid):
                        os.kill(pid, signal.SIGKILL)
            wait_until_stopped(pid)


def stub_process(monkeypatch, communicate, returncode=0):
    proc = SimpleNamespace(
        communicate=communicate, returncode=returncode, stdout=StringIO(),
    )
    monkeypatch.setattr(validate, "start_process", lambda *args, **kwargs: proc)
    return proc


@pytest.mark.parametrize("keep_output", [False, True])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_success_return_contract(tmp_path, monkeypatch, keep_output, exit_code):
    output = "prefix\n" + "x" * 9000
    proc = stub_process(monkeypatch, lambda **kwargs: (output, None), exit_code)
    cleanup = []
    monkeypatch.setattr(validate, "terminate_process_tree", lambda proc, **kwargs: cleanup.append(kwargs))
    result = validate.run_command(["fixture"], cwd=tmp_path, timeout=2, keep_output=keep_output)
    assert result == {
        "cmd": ["fixture"], "exit_code": exit_code, "output_tail": output[-8000:],
        **({"output": output} if keep_output else {}),
    }
    assert cleanup == [{"force": False}]
    assert proc.stdout.closed


@pytest.mark.parametrize("keep_output", [False, True])
def test_timeout_return_contract(tmp_path, monkeypatch, keep_output):
    timeouts = []

    def communicate(timeout):
        timeouts.append(timeout)
        if len(timeouts) == 1:
            raise subprocess.TimeoutExpired(["fixture"], timeout)
        return "partial output", None

    proc = stub_process(monkeypatch, communicate, -signal.SIGTERM)
    cleanup = []
    monkeypatch.setattr(validate, "terminate_process_tree", lambda proc, **kwargs: cleanup.append(kwargs))
    result = validate.run_command(["fixture"], cwd=tmp_path, timeout=2, keep_output=keep_output)
    assert result == {
        "cmd": ["fixture"], "exit_code": None, "timed_out": True,
        "output_tail": "partial output",
        **({"output": "partial output"} if keep_output else {}),
    }
    assert timeouts == [2, 1]
    assert cleanup == [{"force": True}]
    assert proc.stdout.closed


def test_timeout_drain_is_bounded(tmp_path, monkeypatch):
    timeouts = []

    def communicate(timeout):
        timeouts.append(timeout)
        raise subprocess.TimeoutExpired(["fixture"], timeout)

    proc = stub_process(monkeypatch, communicate)
    monkeypatch.setattr(validate, "terminate_process_tree", lambda *args, **kwargs: None)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        validate.run_command(["fixture"], cwd=tmp_path, timeout=2)
    assert caught.value.timeout == 1
    assert timeouts == [2, 1]
    assert proc.stdout.closed


@pytest.mark.parametrize("error", [
    OSError("read failed"), RuntimeError("read failed"), KeyboardInterrupt("interrupted"),
    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid byte"),
])
def test_cleanup_error_preserves_original_error(tmp_path, monkeypatch, error):
    def communicate(**kwargs):
        raise error

    def cleanup(*args, **kwargs):
        raise OSError("cleanup failed")

    proc = stub_process(monkeypatch, communicate)
    monkeypatch.setattr(validate, "terminate_process_tree", cleanup)
    with pytest.raises(type(error)) as caught:
        validate.run_command(["fixture"], cwd=tmp_path, timeout=2)
    assert caught.value is error
    assert proc.stdout.closed


def test_cleanup_error_after_success_is_not_hidden(tmp_path, monkeypatch):
    proc = stub_process(monkeypatch, lambda **kwargs: ("done", None))
    error = OSError("cleanup failed")

    def cleanup(*args, **kwargs):
        raise error

    monkeypatch.setattr(validate, "terminate_process_tree", cleanup)
    with pytest.raises(OSError) as caught:
        validate.run_command(["fixture"], cwd=tmp_path, timeout=2)
    assert caught.value is error
    assert proc.stdout.closed


def test_launch_error_is_unchanged(tmp_path, monkeypatch):
    error = FileNotFoundError("fixture executable absent")

    def start(*args, **kwargs):
        raise error

    monkeypatch.setattr(validate, "start_process", start)
    with pytest.raises(FileNotFoundError) as caught:
        validate.run_command(["fixture"], cwd=tmp_path, timeout=2)
    assert caught.value is error


@pytest.mark.parametrize("alive", [False, True])
def test_non_posix_cleanup_bounds_direct_child_wait(monkeypatch, alive):
    calls = []
    proc = SimpleNamespace(
        poll=lambda: None if alive else 0,
        kill=lambda: calls.append("kill"),
        wait=lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(process, "os", SimpleNamespace(name="nt"))
    process.terminate_process_tree(proc)
    assert calls == (["kill"] if alive else []) + [{"timeout": 1}]
