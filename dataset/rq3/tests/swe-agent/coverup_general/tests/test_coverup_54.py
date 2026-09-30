# file: sweagent/inspector/server.py:215-227
# asked: {"lines": [215, 216, 217, 218, 219, 220, 222, 223, 224, 225, 226, 227], "branches": []}
# gained: {"lines": [215, 216, 217, 218, 219, 220, 222, 223, 224, 225, 226, 227], "branches": []}

import json
from pathlib import Path
import builtins
import types

import pytest

import sweagent.inspector.server as server_module
from sweagent.inspector.server import Handler


class DummyWFile:
    def __init__(self):
        self.data = b""

    def write(self, b: bytes):
        # mimic file-like write
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError("write() argument must be bytes")
        self.data += b
        return len(b)


def make_handler():
    # Create instance without calling SimpleHTTPRequestHandler.__init__
    h = object.__new__(Handler)
    # set placeholders for attributes used by serve_file_content
    h.traj_dir = "/tmp/traj"
    h.gold_patches = {"g": 1}
    h.test_patches = {"t": 2}
    # wiring for recording calls
    h._calls = []
    h.wfile = DummyWFile()

    def send_response(code):
        h._calls.append(("send_response", code))

    def send_header(k, v):
        h._calls.append(("send_header", k, v))

    def end_headers():
        h._calls.append(("end_headers",))

    def send_error(code, msg=None):
        h._calls.append(("send_error", code, msg))

    h.send_response = send_response
    h.send_header = send_header
    h.end_headers = end_headers
    h.send_error = send_error
    return h


def test_serve_file_content_success(monkeypatch):
    # Arrange: patch load_content to return a known dict and capture arguments
    captured = {}

    def fake_load_content(path_arg, gold_arg, test_arg):
        captured['path'] = path_arg
        captured['gold'] = gold_arg
        captured['test'] = test_arg
        return {"k": "v", "num": 42}

    monkeypatch.setattr(server_module, "load_content", fake_load_content)

    h = make_handler()
    # set traj_dir to a known Path-like string
    h.traj_dir = "mytrajdir"
    file_path = "sub/afile.txt"

    # Act
    h.serve_file_content(file_path)

    # Assert load_content was called with Path(traj_dir) / file_path and the patches
    assert isinstance(captured.get('path'), Path)
    assert str(captured['path']) == str(Path("mytrajdir") / file_path)
    assert captured['gold'] == h.gold_patches
    assert captured['test'] == h.test_patches

    # Assert response headers and body written correctly
    assert ("send_response", 200) in h._calls
    assert ("send_header", "Content-type", "text/plain") in h._calls
    assert ("end_headers",) in h._calls

    # body should be JSON dump of the returned content
    expected_body = json.dumps({"k": "v", "num": 42}).encode()
    assert h.wfile.data == expected_body


def test_serve_file_content_not_found(monkeypatch):
    # Arrange: patch load_content to raise FileNotFoundError
    def fake_load_content(path_arg, gold_arg, test_arg):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(server_module, "load_content", fake_load_content)

    h = make_handler()
    h.traj_dir = "/does/not/matter"
    file_path = "missing.txt"

    # Act
    h.serve_file_content(file_path)

    # Assert send_error was called with 404 and expected message
    # The Handler code calls: self.send_error(404, f'File {file_path} not found')
    assert ("send_error", 404, f"File {file_path} not found") in h._calls

    # Ensure no body was written
    assert h.wfile.data == b""
