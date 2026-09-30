import json
import httpx
from types import SimpleNamespace
import pytest

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


class FakeResponse:
    def __init__(self, data=None, json_exc=None):
        self._data = data
        self._json_exc = json_exc

    def json(self):
        if self._json_exc:
            # Raise the provided JSON-related exception
            raise self._json_exc
        return self._data

    def __repr__(self):
        return f"<FakeResponse {self._data!r}>"


def _make_runtime(send_behavior=None, parse_behavior=None, resume_behavior=None):
    """Create a RemoteRuntime instance with controlled behaviors.

    send_behavior: either a FakeResponse to return or an Exception instance to raise
    parse_behavior: callable(response) invoked when _parse_runtime_response is called
    resume_behavior: callable() invoked when _resume_runtime is called
    """
    rt = object.__new__(RemoteRuntime)
    # minimal attributes used by _check_existing_runtime
    rt.sid = "session-123"
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url="http://example.local"))

    # capture logs for assertions
    rt._captured_logs = []

    def log(level, message, exc_info=False):
        rt._captured_logs.append((level, message, exc_info))

    rt.log = log

    # define _send_runtime_api_request behavior
    def _send_runtime_api_request(method, url, **kwargs):
        if isinstance(send_behavior, Exception):
            raise send_behavior
        return send_behavior

    rt._send_runtime_api_request = _send_runtime_api_request

    # provide optional parse and resume behaviors
    rt._parse_called = []

    def _parse_runtime_response(response):
        rt._parse_called.append(response)
        if callable(parse_behavior):
            return parse_behavior(response)

    rt._parse_runtime_response = _parse_runtime_response

    rt._resume_called = 0

    def _resume_runtime():
        rt._resume_called += 1
        if callable(resume_behavior):
            return resume_behavior()

    rt._resume_runtime = _resume_runtime

    return rt


def test_running_runtime_round_030():
    # When API returns status 'running', parse should be called and True returned
    resp = FakeResponse({"status": "running"})
    rt = _make_runtime(send_behavior=resp)

    result = rt._check_existing_runtime()

    assert result is True
    # parse should be called exactly once with the response object
    assert rt._parse_called == [resp]
    # check that the logs include the running-state message
    assert any("running state" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_paused_resume_success_round_030():
    # When status is 'paused' and resume succeeds, should return True
    resp = FakeResponse({"status": "paused"})

    def resume_ok():
        return None

    rt = _make_runtime(send_behavior=resp, resume_behavior=resume_ok)

    result = rt._check_existing_runtime()

    assert result is True
    assert rt._parse_called == [resp]
    assert rt._resume_called == 1
    assert any("resumed paused runtime" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_paused_resume_fail_round_030():
    # When status is 'paused' but resume raises, should log error and return False
    resp = FakeResponse({"status": "paused"})

    def resume_fail():
        raise RuntimeError("resume failed")

    rt = _make_runtime(send_behavior=resp, resume_behavior=resume_fail)

    result = rt._check_existing_runtime()

    assert result is False
    assert rt._parse_called == [resp]
    assert rt._resume_called == 1
    assert any("Failed to resume paused runtime" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_stopped_status_round_030():
    # When status is 'stopped', should not call parse and return False
    resp = FakeResponse({"status": "stopped"})
    rt = _make_runtime(send_behavior=resp)

    result = rt._check_existing_runtime()

    assert result is False
    assert rt._parse_called == []
    assert any("it is stopped" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_invalid_status_round_030():
    # Unknown status value should cause error log and return False
    resp = FakeResponse({"status": "weird_status"})
    rt = _make_runtime(send_behavior=resp)

    result = rt._check_existing_runtime()

    assert result is False
    # verify the error log about invalid response appears
    assert any("Invalid response from runtime API" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_http_404_round_030():
    # If the request raises httpx.HTTPError with response.status_code == 404 -> return False
    e = httpx.HTTPError("not found")
    e.response = SimpleNamespace(status_code=404)
    rt = _make_runtime(send_behavior=e)

    result = rt._check_existing_runtime()

    assert result is False
    assert any("No existing runtime found" in (msg or "") for _, msg, _ in rt._captured_logs)


def test_http_500_round_030():
    # If the request raises httpx.HTTPError with non-404 status -> should re-raise
    e = httpx.HTTPError("server error")
    e.response = SimpleNamespace(status_code=500)
    rt = _make_runtime(send_behavior=e)

    with pytest.raises(httpx.HTTPError):
        rt._check_existing_runtime()


def test_json_decode_error_round_030():
    # If response.json() raises JSONDecodeError, the method should log and re-raise
    json_err = json.decoder.JSONDecodeError("msg", "doc", 0)
    resp = FakeResponse(json_exc=json_err)
    rt = _make_runtime(send_behavior=resp)

    with pytest.raises(json.decoder.JSONDecodeError):
        rt._check_existing_runtime()

    # ensure error log was recorded
    assert any("Invalid JSON response from runtime API" in (msg or "") for _, msg, _ in rt._captured_logs)
