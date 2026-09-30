import signal
from pathlib import Path
from collections import defaultdict
import pytest

import rdagent.log.server.app as appmod


class FakeProc:
    def __init__(self, pid=123, poll_value=None):
        self.pid = pid
        self._poll = poll_value
        self.terminated = False
        self.wait_called = False

    def poll(self):
        return self._poll

    def terminate(self):
        self.terminated = True

    def wait(self):
        self.wait_called = True


def _call_control_and_extract():
    """Call control_process and normalize return (status_code, json_body)"""
    resp = appmod.control_process()
    if isinstance(resp, tuple):
        response_obj, status = resp
    else:
        response_obj = resp
        status = getattr(response_obj, "status_code", None)
    body = response_obj.get_json() if hasattr(response_obj, "get_json") else None
    return status, body


def setup_globals(base_path=Path("/base")):
    # Ensure deterministic global state for each test
    appmod.rdagent_processes = {}
    appmod.msgs_for_frontend = defaultdict(list)
    appmod.log_folder_path = base_path


def test_control_missing_json_round_074():
    """Missing JSON should return 400 with missing id/action message"""
    setup_globals()
    # request with no json -> get_json() returns None
    with appmod.app.test_request_context(path="/control", method="POST"):
        status, body = _call_control_and_extract()
    assert status == 400
    assert isinstance(body, dict)
    assert "Missing 'id' or 'action' in request" in body.get("error", "")


def test_control_missing_action_round_074():
    """JSON missing 'action' key should return 400"""
    setup_globals()
    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess"}):
        status, body = _call_control_and_extract()
    assert status == 400
    assert "Missing 'id' or 'action' in request" in body.get("error", "")


def test_control_no_running_process_round_074():
    """If id not present in rdagent_processes, returns 400 and message about no running process"""
    setup_globals()
    # Use id that will be converted to a path string
    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "pause"}):
        status, body = _call_control_and_extract()
    assert status == 400
    assert body and body.get("error") and "No running process" in body["error"]


def test_control_process_already_terminated_round_074():
    """If process.poll() is not None, append END and return 400"""
    setup_globals()
    id_key = str(appmod.log_folder_path / "sess")
    proc = FakeProc(pid=11, poll_value=1)  # non-None -> already terminated
    appmod.rdagent_processes[id_key] = proc
    # ensure msgs_for_frontend list exists
    appmod.msgs_for_frontend[id_key] = []

    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "pause"}):
        status, body = _call_control_and_extract()

    assert status == 400
    # ensure an END tag appended to frontend messages
    assert any(isinstance(m, dict) and m.get("tag") == "END" for m in appmod.msgs_for_frontend[id_key])
    assert body and "Process has already terminated" in body.get("error", "")


def test_control_pause_and_resume_round_074(monkeypatch):
    """Pause should call os.kill with SIGSTOP; resume should call SIGCONT."""
    setup_globals()
    id_key = str(appmod.log_folder_path / "sess")

    # Prepare process for pause test
    proc_pause = FakeProc(pid=999, poll_value=None)
    appmod.rdagent_processes[id_key] = proc_pause
    appmod.msgs_for_frontend[id_key] = []

    called = []

    def fake_kill(pid, sig):
        called.append((pid, sig))

    monkeypatch.setattr(appmod.os, "kill", fake_kill, raising=False)

    # Pause
    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "pause"}):
        status, body = _call_control_and_extract()

    assert status == 200
    assert body and body.get("status") == "paused"
    assert called and called[-1][0] == proc_pause.pid and called[-1][1] == signal.SIGSTOP

    # Prepare process for resume test
    proc_resume = FakeProc(pid=1000, poll_value=None)
    appmod.rdagent_processes[id_key] = proc_resume
    called.clear()

    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "resume"}):
        status, body = _call_control_and_extract()

    assert status == 200
    assert body and body.get("status") == "resumed"
    assert called and called[-1][0] == proc_resume.pid and called[-1][1] == signal.SIGCONT


def test_control_pause_raises_and_returns_500_round_074(monkeypatch):
    """If os.kill raises, the exception is caught and a 500 is returned with message"""
    setup_globals()
    id_key = str(appmod.log_folder_path / "sess")
    proc = FakeProc(pid=321, poll_value=None)
    appmod.rdagent_processes[id_key] = proc

    def raising_kill(pid, sig):
        raise RuntimeError("boom")

    monkeypatch.setattr(appmod.os, "kill", raising_kill, raising=False)

    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "pause"}):
        status, body = _call_control_and_extract()

    assert status == 500
    assert body and "Failed to pause process" in body.get("error", "")
    assert "boom" in body.get("error")


def test_control_stop_removes_process_and_appends_end_round_074():
    """Stop should call terminate/wait, remove process from registry and append END"""
    setup_globals()
    id_key = str(appmod.log_folder_path / "sess")
    proc = FakeProc(pid=444, poll_value=None)
    appmod.rdagent_processes[id_key] = proc
    appmod.msgs_for_frontend[id_key] = []

    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "stop"}):
        status, body = _call_control_and_extract()

    assert status == 200
    assert body and body.get("status") == "stopped"
    # ensure terminate and wait were invoked
    assert proc.terminated is True
    assert proc.wait_called is True
    # process removed from registry
    assert id_key not in appmod.rdagent_processes
    # ensure END appended
    assert any(isinstance(m, dict) and m.get("tag") == "END" for m in appmod.msgs_for_frontend[id_key])


def test_control_unknown_action_round_074():
    """Unknown action should return 400 and Unknown action message"""
    setup_globals()
    id_key = str(appmod.log_folder_path / "sess")
    # Put a running-looking process so flow reaches the unknown action branch
    proc = FakeProc(pid=55, poll_value=None)
    appmod.rdagent_processes[id_key] = proc
    appmod.msgs_for_frontend[id_key] = []

    with appmod.app.test_request_context(path="/control", method="POST", json={"id": "sess", "action": "nope"}):
        status, body = _call_control_and_extract()

    assert status == 400
    assert body and "Unknown action" in body.get("error", "")
