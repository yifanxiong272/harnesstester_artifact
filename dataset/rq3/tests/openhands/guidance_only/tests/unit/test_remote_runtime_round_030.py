import json
from types import SimpleNamespace
import pytest
import httpx
from json.decoder import JSONDecodeError

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


class FakeResponse:
    def __init__(self, data=None, json_exc=None):
        self._data = data
        self._json_exc = json_exc

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._data

    def __repr__(self):
        return f"<FakeResponse data={self._data!r}>"


class FakeHTTPError(httpx.HTTPError):
    def __init__(self, status_code: int):
        # Give an object that looks like httpx.Response with status_code
        self.response = SimpleNamespace(status_code=status_code)
        super().__init__(f"HTTP {status_code}")


def make_stub_runtime():
    # Create a RemoteRuntime instance without invoking __init__ and patch minimal attrs
    inst = object.__new__(RemoteRuntime)
    inst.sid = "session-123"
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url="https://example.com/api"))
    inst._parse_runtime_response = lambda resp: None
    inst._resume_runtime = lambda: None
    logs = []

    def log(level, message, exc_info=False):
        # mirror signature used in code: log(self, level, message, exc_info)
        logs.append((level, message, exc_info))

    inst.log = log
    inst._last_logs = logs
    return inst


def test_running_status_round_030():
    inst = make_stub_runtime()
    response = FakeResponse({"status": "running"})

    parse_called = {"v": False}

    def parse(resp):
        # ensure the same response object is passed
        parse_called["v"] = True
        assert resp is response

    inst._parse_runtime_response = parse
    inst._send_runtime_api_request = lambda method, url: response

    result = inst._check_existing_runtime()

    assert result is True
    assert parse_called["v"] is True
    # last log should indicate runtime found running
    assert any("Found existing runtime in running state" in msg for _, msg, _ in inst._last_logs)


def test_paused_resume_success_round_030():
    inst = make_stub_runtime()
    response = FakeResponse({"status": "paused"})

    resume_called = {"v": False}

    def resume():
        resume_called["v"] = True
        return None

    inst._resume_runtime = resume
    inst._send_runtime_api_request = lambda method, url: response

    result = inst._check_existing_runtime()

    assert result is True
    assert resume_called["v"] is True
    assert any("Successfully resumed paused runtime" in msg for _, msg, _ in inst._last_logs)


def test_paused_resume_failure_round_030():
    inst = make_stub_runtime()
    response = FakeResponse({"status": "paused"})

    def resume():
        raise Exception("boom")

    inst._resume_runtime = resume
    inst._send_runtime_api_request = lambda method, url: response

    result = inst._check_existing_runtime()

    # Should catch exception from resume and return False
    assert result is False
    # There should be an error log referring to failure to resume
    assert any("Failed to resume paused runtime" in msg for _, msg, _ in inst._last_logs)


def test_stopped_status_round_030():
    inst = make_stub_runtime()
    response = FakeResponse({"status": "stopped"})
    inst._send_runtime_api_request = lambda method, url: response

    result = inst._check_existing_runtime()

    assert result is False
    assert any("Found existing runtime, but it is stopped" in msg for _, msg, _ in inst._last_logs)


def test_http_404_round_030():
    inst = make_stub_runtime()

    def raise_404(method, url):
        raise FakeHTTPError(404)

    inst._send_runtime_api_request = raise_404

    result = inst._check_existing_runtime()

    # 404 should be interpreted as no runtime found and return False
    assert result is False
    assert any("No existing runtime found for session ID" in msg for _, msg, _ in inst._last_logs)


def test_http_other_error_round_030():
    inst = make_stub_runtime()

    def raise_500(method, url):
        raise FakeHTTPError(500)

    inst._send_runtime_api_request = raise_500

    with pytest.raises(httpx.HTTPError):
        inst._check_existing_runtime()

    # There should be an error log recorded before re-raising
    assert any("Error while looking for remote runtime" in msg for _, msg, _ in inst._last_logs)


def test_json_decode_round_030():
    inst = make_stub_runtime()
    # response.json() will raise JSONDecodeError
    json_err = JSONDecodeError("Expecting value", "doc", 0)
    response = FakeResponse(json_exc=json_err)
    inst._send_runtime_api_request = lambda method, url: response

    with pytest.raises(JSONDecodeError):
        inst._check_existing_runtime()

    # Should have logged an error about invalid JSON response
    assert any("Invalid JSON response from runtime API" in msg for _, msg, _ in inst._last_logs)


def test_invalid_status_round_030():
    inst = make_stub_runtime()
    response = FakeResponse({"status": "weird_status"})
    inst._send_runtime_api_request = lambda method, url: response

    result = inst._check_existing_runtime()

    assert result is False
    assert any("Invalid response from runtime API" in msg for _, msg, _ in inst._last_logs)
