# file: sweagent/inspector/server.py:256-263
# asked: {"lines": [256, 257, 258, 259, 260, 262, 263], "branches": [[258, 259], [258, 262]]}
# gained: {"lines": [256, 257, 258, 259, 260, 262, 263], "branches": [[258, 259], [258, 262]]}

import types
import os
from pathlib import Path

import pytest

from sweagent.inspector import server


def _make_bound_methods(h, calls):
    def fake_send_response(self, code):
        calls.append(("send_response", code))

    def fake_end_headers(self):
        calls.append(("end_headers",))

    h.send_response = types.MethodType(fake_send_response, h)
    h.end_headers = types.MethodType(fake_end_headers, h)


def _current_mod_times_for_dir(dirpath):
    return {str(file): file.stat().st_mtime for file in Path(dirpath).glob("**/*.traj")}


def test_check_for_updates_sends_200_on_change(tmp_path, monkeypatch):
    # Arrange: create a .traj file in the directory
    traj_file = tmp_path / "example.traj"
    traj_file.write_text("data")
    # Ensure file system flush
    os.utime(traj_file, None)

    # Start with an empty mapping so the handler should detect a change
    monkeypatch.setattr(server.Handler, "file_mod_times", {}, raising=False)

    # Create a handler instance without calling its constructor and bind fake methods
    h = server.Handler.__new__(server.Handler)
    h.traj_dir = str(tmp_path)
    calls = []
    _make_bound_methods(h, calls)

    # Act
    h.check_for_updates()

    # Assert: send_response(200) then end_headers called
    assert calls == [("send_response", 200), ("end_headers",)]

    # And the class-level file_mod_times should now reflect the file we created
    mod_times = server.Handler.file_mod_times
    assert isinstance(mod_times, dict)
    expected_key = str(traj_file)
    assert expected_key in mod_times
    # The stored mtime should match the actual file's mtime
    assert pytest.approx(traj_file.stat().st_mtime, rel=1e-6) == mod_times[expected_key]


def test_check_for_updates_sends_204_when_no_change(tmp_path, monkeypatch):
    # Arrange: create a .traj file in the directory
    traj_file = tmp_path / "nested" / "same.traj"
    traj_file.parent.mkdir(parents=True, exist_ok=True)
    traj_file.write_text("content")
    os.utime(traj_file, None)

    # Compute current mapping and set it as the Handler's file_mod_times so no update is detected
    current = _current_mod_times_for_dir(tmp_path)
    monkeypatch.setattr(server.Handler, "file_mod_times", current, raising=False)

    # Create handler instance and bind fake methods
    h = server.Handler.__new__(server.Handler)
    h.traj_dir = str(tmp_path)
    calls = []
    _make_bound_methods(h, calls)

    # Act
    h.check_for_updates()

    # Assert: send_response(204) then end_headers called
    assert calls == [("send_response", 204), ("end_headers",)]

    # And file_mod_times remains equal to what we set (no mutation)
    assert server.Handler.file_mod_times == current
