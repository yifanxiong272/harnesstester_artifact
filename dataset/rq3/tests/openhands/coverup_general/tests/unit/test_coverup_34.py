# file: openhands/runtime/impl/remote/remote_runtime.py:180-229
# asked: {"lines": [181, 182, 183, 184, 185, 187, 188, 189, 190, 191, 192, 193, 194, 195, 197, 198, 199, 200, 201, 202, 203, 205, 207, 208, 209, 210, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 222, 223, 226, 228, 229], "branches": [[190, 191], [190, 207], [193, 194], [193, 198], [207, 208], [207, 210], [210, 211], [210, 213], [213, 214], [213, 228]]}
# gained: {"lines": [181, 182, 183, 184, 185, 187, 188, 189, 190, 191, 192, 193, 194, 195, 197, 198, 199, 200, 201, 202, 203, 205, 207, 208, 209, 210, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 222, 223, 226, 228, 229], "branches": [[190, 191], [190, 207], [193, 194], [193, 198], [207, 208], [207, 210], [210, 211], [210, 213], [213, 214], [213, 228]]}

import json
import types

import httpx
import pytest

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


class DummyResponse:
    def __init__(self, data=None, raise_json=False):
        self._data = data
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            # raise a JSONDecodeError similar to what json library produces
            raise json.decoder.JSONDecodeError("Expecting value", "doc", 0)
        return self._data

    def __repr__(self):
        return f"<DummyResponse data={self._data!r}>"


def make_runtime_instance():
    """
    Create a RemoteRuntime instance without calling its __init__,
    and set minimal attributes used by _check_existing_runtime.
    """
    inst = object.__new__(RemoteRuntime)
    inst.sid = "session-123"
    inst.config = types.SimpleNamespace(
        sandbox=types.SimpleNamespace(remote_runtime_api_url="https://example.com/api")
    )
    # simple logger that records messages
    inst._logs = []

    def log(level, msg, **kwargs):
        inst._logs.append((level, msg, kwargs))

    inst.log = log
    return inst


def test_check_existing_runtime_running_calls_parse_and_returns_true():
    rt = make_runtime_instance()
    called = {"parse": 0}

    def send_req(method, url):
        assert method == "GET"
        assert url.endswith(f"/sessions/{rt.sid}")
        return DummyResponse({"status": "running", "other": "x"})

    def parse_resp(response):
        called["parse"] += 1
        # ensure response passed through
        assert isinstance(response, DummyResponse)

    rt._send_runtime_api_request = send_req
    rt._parse_runtime_response = parse_resp

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is True
    assert called["parse"] == 1
    # ensure an info log about running state exists
    assert any("running state" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_stopped_returns_false_and_no_parse():
    rt = make_runtime_instance()
    called = {"parse": 0}

    def send_req(method, url):
        return DummyResponse({"status": "stopped"})

    def parse_resp(response):
        called["parse"] += 1

    rt._send_runtime_api_request = send_req
    rt._parse_runtime_response = parse_resp

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is False
    assert called["parse"] == 0
    assert any("but it is stopped" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_paused_resume_success():
    rt = make_runtime_instance()
    called = {"parse": 0, "resume": 0}

    def send_req(method, url):
        return DummyResponse({"status": "paused"})

    def parse_resp(response):
        called["parse"] += 1

    def resume():
        called["resume"] += 1
        # succeed silently

    rt._send_runtime_api_request = send_req
    rt._parse_runtime_response = parse_resp
    rt._resume_runtime = resume

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is True
    assert called["parse"] == 1
    assert called["resume"] == 1
    assert any("Successfully resumed paused runtime" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_paused_resume_failure_returns_false_and_logs_error():
    rt = make_runtime_instance()
    called = {"parse": 0, "resume": 0}

    def send_req(method, url):
        return DummyResponse({"status": "paused"})

    def parse_resp(response):
        called["parse"] += 1

    def resume():
        called["resume"] += 1
        raise RuntimeError("cannot resume")

    rt._send_runtime_api_request = send_req
    rt._parse_runtime_response = parse_resp
    rt._resume_runtime = resume

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is False
    assert called["parse"] == 1
    assert called["resume"] == 1
    # ensure error log about failing to resume exists
    assert any("Failed to resume paused runtime" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_invalid_status_logs_and_returns_false():
    rt = make_runtime_instance()

    def send_req(method, url):
        return DummyResponse({"status": "weird", "foo": "bar"})

    rt._send_runtime_api_request = send_req
    # don't provide parse/resume since they shouldn't be called

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is False
    # ensure error logged about invalid response includes the data representation
    assert any("Invalid response from runtime API" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_http_404_returns_false():
    rt = make_runtime_instance()

    def send_req(method, url):
        e = httpx.HTTPError("not found")
        # attach a response-like object with status_code
        e.response = types.SimpleNamespace(status_code=404)
        raise e

    rt._send_runtime_api_request = send_req

    result = RemoteRuntime._check_existing_runtime(rt)
    assert result is False
    assert any("No existing runtime found for session ID" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_http_other_raises():
    rt = make_runtime_instance()

    def send_req(method, url):
        e = httpx.HTTPError("server error")
        e.response = types.SimpleNamespace(status_code=500)
        raise e

    rt._send_runtime_api_request = send_req

    with pytest.raises(httpx.HTTPError):
        RemoteRuntime._check_existing_runtime(rt)
    # ensure error log about looking for remote runtime exists (logged before raising)
    assert any("Error while looking for remote runtime" in msg for _, msg, _ in rt._logs)


def test_check_existing_runtime_invalid_json_raises():
    rt = make_runtime_instance()

    def send_req(method, url):
        return DummyResponse(raise_json=True)

    rt._send_runtime_api_request = send_req

    with pytest.raises(json.decoder.JSONDecodeError):
        RemoteRuntime._check_existing_runtime(rt)
    assert any("Invalid JSON response from runtime API" in msg for _, msg, _ in rt._logs)
