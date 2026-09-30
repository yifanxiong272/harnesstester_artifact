# file: browser_use/skill_cli/main.py:991-1066
# asked: {"lines": [993, 994, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1006, 1007, 1009, 1011, 1012, 1013, 1019, 1020, 1023, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1046, 1048, 1051, 1052, 1053, 1054, 1056, 1057, 1059, 1060, 1061, 1062, 1064, 1066], "branches": [[998, 999], [998, 1001], [999, 998], [999, 1000], [1001, 1002], [1001, 1006], [1003, 1001], [1003, 1004], [1006, 1007], [1006, 1051], [1009, 1011], [1009, 1019], [1011, 1012], [1011, 1019], [1019, 1020], [1019, 1023], [1026, 1027], [1026, 1046], [1029, 1030], [1029, 1048], [1032, 1033], [1032, 1034], [1034, 1035], [1034, 1036], [1036, 1037], [1036, 1040], [1038, 1039], [1038, 1040], [1040, 1041], [1040, 1042], [1052, 1053], [1052, 1056], [1053, 1052], [1053, 1054], [1056, 1057], [1056, 1059], [1059, 1060], [1059, 1064], [1061, 1062], [1061, 1066]]}
# gained: {"lines": [993, 994, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1006, 1007, 1009, 1011, 1012, 1013, 1019, 1020, 1023, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1042, 1043, 1044, 1048, 1051, 1052, 1053, 1054, 1056, 1057, 1059, 1060, 1061, 1062, 1066], "branches": [[998, 999], [998, 1001], [999, 1000], [1001, 1002], [1001, 1006], [1003, 1004], [1006, 1007], [1006, 1051], [1009, 1011], [1009, 1019], [1011, 1012], [1011, 1019], [1019, 1020], [1019, 1023], [1026, 1027], [1029, 1030], [1032, 1033], [1034, 1035], [1036, 1037], [1038, 1039], [1040, 1042], [1052, 1053], [1052, 1056], [1053, 1052], [1053, 1054], [1056, 1057], [1056, 1059], [1059, 1060], [1061, 1062], [1061, 1066]]}

import argparse
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from browser_use.skill_cli import main as mod


def test_handle_sessions_cleans_and_reports_json(tmp_path, monkeypatch, capsys):
    # Prepare files: orphan (should be cleaned) and s1 (live but stopped -> state file removed)
    orphan_pid = tmp_path / "orphan.pid"
    orphan_pid.write_text("123")
    orphan_sock = tmp_path / "orphan.sock"
    orphan_sock.write_text("sock")
    orphan_state = tmp_path / "orphan.state.json"
    orphan_state.write_text('{"x":1}')

    s1_pid = tmp_path / "s1.pid"
    s1_pid.write_text("456")
    s1_sock = tmp_path / "s1.sock"
    s1_sock.write_text("sock")
    s1_state = tmp_path / "s1.state.json"
    s1_state.write_text('{"phase":"stopped"}')

    # Track calls to _clean_session_files
    cleaned = []

    def fake_clean(name: str):
        cleaned.append(name)
        # mimic deletion of pid and sock/state for cleanliness
        for p in (tmp_path / f"{name}.pid", tmp_path / f"{name}.sock", tmp_path / f"{name}.state.json"):
            if p.exists():
                p.unlink()

    # _get_home_dir should return our tmp_path
    monkeypatch.setattr(mod, "_get_home_dir", lambda: tmp_path)
    # _clean_session_files should be our fake_clean
    monkeypatch.setattr(mod, "_clean_session_files", fake_clean)
    # _get_state_path should return the actual path so unlink works in _handle_sessions
    monkeypatch.setattr(mod, "_get_state_path", lambda name: tmp_path / f"{name}.state.json")

    # Prepare probe behavior
    def fake_probe(name: str):
        if name == "orphan":
            return SimpleNamespace(pid_alive=False, socket_reachable=False, phase=None, pid=None)
        elif name == "s1":
            # PID dead but socket reachable; phase is 'stopped' so state file should be unlinked
            return SimpleNamespace(pid_alive=False, socket_reachable=True, phase="stopped", pid=None)
        else:
            pytest.fail(f"Unexpected probe name {name}")

    monkeypatch.setattr(mod, "_probe_session", fake_probe)

    # send_command for s1 should return success with data that tests headed/profile/cdp
    def fake_send_command(cmd, payload, session=None):
        assert cmd == "ping"
        if session == "s1":
            return {
                "success": True,
                "data": {"headed": True, "profile": "pro", "cdp_url": "http://cdp", "use_cloud": False},
            }
        raise AssertionError("Unexpected session in send_command")

    monkeypatch.setattr(mod, "send_command", fake_send_command)

    # Run with json output
    args = argparse.Namespace(json=True)
    ret = mod._handle_sessions(args)
    assert ret == 0

    # Capture and parse JSON output
    captured = capsys.readouterr()
    out = captured.out.strip()
    obj = json.loads(out)
    assert "sessions" in obj
    sessions = obj["sessions"]
    # Only s1 should be reported; orphan should have been cleaned and not present
    assert len(sessions) == 1
    s = sessions[0]
    assert s["name"] == "s1"
    # pid was None -> becomes 0
    assert s["pid"] == 0
    # phase was 'stopped' but session live -> shown as 'stopped'
    assert s["phase"] == "stopped"
    # config string should include headed, profile and cdp
    assert "headed" in s.get("config", "")
    assert "profile=pro" in s.get("config", "")
    assert "cdp" in s.get("config", "")
    # cdp_url should be present
    assert s["cdp_url"] == "http://cdp"

    # Check that fake_clean was called for orphan
    assert "orphan" in cleaned

    # State file for s1 should have been removed by _get_state_path(...).unlink
    assert not s1_state.exists()
    # orphan.sock should be removed by the socket sweep
    assert not orphan_sock.exists()
    # s1.sock should remain (live session)
    assert s1_sock.exists()


def test_handle_sessions_send_exception_and_table_output(tmp_path, monkeypatch, capsys):
    # Prepare files: x (live and reachable but send_command raises -> config='?') and orphan.sock to be removed
    x_pid = tmp_path / "x.pid"
    x_pid.write_text("999")
    x_sock = tmp_path / "x.sock"
    x_sock.write_text("sock")

    orphan_sock = tmp_path / "orphan.sock"
    orphan_sock.write_text("sock")

    monkeypatch.setattr(mod, "_get_home_dir", lambda: tmp_path)
    # _get_state_path not used here but provide a safe lambda
    monkeypatch.setattr(mod, "_get_state_path", lambda name: tmp_path / f"{name}.state.json")

    # probe for x is live and reachable
    def fake_probe(name: str):
        if name == "x":
            return SimpleNamespace(pid_alive=True, socket_reachable=True, phase="running", pid=12345)
        pytest.fail(f"Unexpected probe name {name}")

    monkeypatch.setattr(mod, "_probe_session", fake_probe)

    # send_command for x raises exception -> should set config to '?'
    def fake_send_command(cmd, payload, session=None):
        raise RuntimeError("ping failed")

    monkeypatch.setattr(mod, "send_command", fake_send_command)

    # Ensure _clean_session_files not called inadvertently
    called = []

    def fake_clean(name: str):
        called.append(name)

    monkeypatch.setattr(mod, "_clean_session_files", fake_clean)

    args = argparse.Namespace(json=False)
    ret = mod._handle_sessions(args)
    assert ret == 0

    captured = capsys.readouterr()
    out = captured.out

    # Should print header and the x session line
    assert "SESSION" in out
    assert "PHASE" in out
    # The session name and pid should be present
    assert "x" in out
    assert "12345" in out
    # Because send_command raised, config should be '?'
    assert "?" in out

    # orphan.sock should have been removed by socket sweep
    assert not orphan_sock.exists()
    # x.sock should remain because it's a live name
    assert x_sock.exists()
    # _clean_session_files should not have been called
    assert called == []
