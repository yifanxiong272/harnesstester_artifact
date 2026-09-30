import json
from types import SimpleNamespace
import pytest
import httpx
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


class FakeResponse:
    def __init__(self, data=None, json_error=None):
        self._data = data
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._data

    def __str__(self):
        return f"FakeResponse({self._data!r})"


def make_runtime():
    # Create instance without calling RemoteRuntime.__init__
    inst = object.__new__(RemoteRuntime)
    inst.sid = "session-123"
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url="http://example.api"))
    inst.logs = []

    def log(level, message, exc_info=False):
        # simple logger capture for assertions
        inst.logs.append((level, message, exc_info))

    inst.log = log
    return inst


def test_running_status_round_030():
    rt = make_runtime()

    resp = FakeResponse({"status": "running"})

    called = {"parsed": False}

    def fake_send(method, url):
        assert method == "GET"
        assert url == f"{rt.config.sandbox.remote_runtime_api_url}/sessions/{rt.sid}"
        return resp

    def fake_parse(response):
        assert response is resp
        called["parsed"] = True

    rt._send_runtime_api_request = fake_send
    rt._parse_runtime_response = fake_parse

    result = rt._check_existing_runtime()

    assert result is True
    assert called["parsed"] is True
    # ensure a log entry about running state was recorded
    assert any("Found existing runtime in running state" in msg for _, msg, _ in rt.logs)


def test_stopped_status_round_030():
    rt = make_runtime()

    resp = FakeResponse({"status": "stopped"})

    rt._send_runtime_api_request = lambda method, url: resp

    # parse should not be called for 'stopped'
    rt._parse_runtime_response = lambda response: (_ for _ in ()).throw(AssertionError("_parse_runtime_response should not be called"))

    result = rt._check_existing_runtime()

    assert result is False
    assert any("but it is stopped" in msg for _, msg, _ in rt.logs)


def test_paused_resume_success_round_030():
    rt = make_runtime()

    resp = FakeResponse({"status": "paused"})

    rt._send_runtime_api_request = lambda method, url: resp

    parsed = {"ok": False}

    def fake_parse(response):
        parsed["ok"] = True

    resumed = {"ok": False}

    def fake_resume():
        resumed["ok"] = True

    rt._parse_runtime_response = fake_parse
    rt._resume_runtime = fake_resume

    result = rt._check_existing_runtime()

    assert result is True
    assert parsed["ok"] is True
    assert resumed["ok"] is True
    assert any("Successfully resumed paused runtime" in msg for _, msg, _ in rt.logs)


def test_paused_resume_failure_round_030():
    rt = make_runtime()

    resp = FakeResponse({"status": "paused"})

    rt._send_runtime_api_request = lambda method, url: resp

    rt._parse_runtime_response = lambda response: None

    def fake_resume():
        raise RuntimeError("resume failed")

    rt._resume_runtime = fake_resume

    result = rt._check_existing_runtime()

    assert result is False
    assert any("Failed to resume paused runtime" in msg for _, msg, _ in rt.logs)


def test_http_404_round_030():
    rt = make_runtime()

    def raise_404(method, url):
        e = httpx.HTTPError("http error")
        e.response = SimpleNamespace(status_code=404)
        raise e

    rt._send_runtime_api_request = raise_404

    result = rt._check_existing_runtime()

    assert result is False
    assert any("No existing runtime found for session ID" in msg for _, msg, _ in rt.logs)


def test_http_non_404_raises_round_030():
    rt = make_runtime()

    def raise_500(method, url):
        e = httpx.HTTPError("http error")
        e.response = SimpleNamespace(status_code=500)
        raise e

    rt._send_runtime_api_request = raise_500

    with pytest.raises(httpx.HTTPError):
        rt._check_existing_runtime()


def test_invalid_json_response_round_030():
    rt = make_runtime()

    # response.json() raises JSONDecodeError
    json_err = json.decoder.JSONDecodeError("msg", "doc", 0)
    resp = FakeResponse(json_error=json_err)

    rt._send_runtime_api_request = lambda method, url: resp

    with pytest.raises(json.decoder.JSONDecodeError):
        rt._check_existing_runtime()

    # ensure the error was logged
    assert any("Invalid JSON response from runtime API" in msg for _, msg, _ in rt.logs)


def test_invalid_status_value_round_030():
    rt = make_runtime()

    resp = FakeResponse({"status": "unexpected_status", "other": "x"})

    rt._send_runtime_api_request = lambda method, url: resp
    rt._parse_runtime_response = lambda response: None

    result = rt._check_existing_runtime()

    assert result is False
    # The error log should contain the data dict representation
    assert any("Invalid response from runtime API" in msg for _, msg, _ in rt.logs)
