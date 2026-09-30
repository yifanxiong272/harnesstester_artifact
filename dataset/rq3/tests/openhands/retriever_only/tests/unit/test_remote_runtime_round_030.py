import json
import httpx
from types import SimpleNamespace
import pytest

from openhands.runtime.impl.remote import remote_runtime

RemoteRuntime = remote_runtime.RemoteRuntime


class FakeSelf:
    def __init__(self, base_url="http://example.com"):
        self.sid = "fake-session"
        self.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url=base_url))
        self.log_calls = []
        # these will be set by individual tests
        self._send_runtime_api_request = None
        self._parse_runtime_response = None
        self._resume_runtime = None

    def log(self, level, message, exc_info=False):
        # record log calls for observable assertions
        self.log_calls.append((level, message, exc_info))


def test_running_status_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()
    response.json = lambda: {"status": "running"}

    parse_called = []

    def parse(resp):
        parse_called.append(resp)

    fake._send_runtime_api_request = lambda method, url: response
    fake._parse_runtime_response = parse

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is True
    # _parse_runtime_response must have been invoked with the response
    assert parse_called == [response]
    # log must include the running-state message
    assert any("Found existing runtime in running state" in m for _, m, _ in fake.log_calls)


def test_stopped_status_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()
    response.json = lambda: {"status": "stopped"}

    fake._send_runtime_api_request = lambda method, url: response

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is False
    # should have logged that the runtime was found but is stopped
    assert any("Found existing runtime, but it is stopped" in m for _, m, _ in fake.log_calls)


def test_paused_resume_success_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()
    response.json = lambda: {"status": "paused"}

    parse_called = []
    resumed = []

    fake._send_runtime_api_request = lambda method, url: response

    def parse(resp):
        parse_called.append(resp)

    def resume():
        resumed.append(True)

    fake._parse_runtime_response = parse
    fake._resume_runtime = resume

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is True
    assert parse_called == [response]
    assert resumed == [True]
    assert any("Successfully resumed paused runtime" in m for _, m, _ in fake.log_calls)


def test_paused_resume_failure_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()
    response.json = lambda: {"status": "paused"}

    fake._send_runtime_api_request = lambda method, url: response
    fake._parse_runtime_response = lambda resp: None

    class ResumeError(Exception):
        pass

    def bad_resume():
        raise ResumeError("cannot resume")

    fake._resume_runtime = bad_resume

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is False
    # log should contain an error about failing to resume
    assert any("Failed to resume paused runtime" in m for _, m, _ in fake.log_calls)


def test_invalid_status_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()
    response.json = lambda: {"status": "mystery_status"}

    fake._send_runtime_api_request = lambda method, url: response

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is False
    # should have logged an invalid-response error with the returned data
    assert any("Invalid response from runtime API" in m for _, m, _ in fake.log_calls)


def test_http_404_round_030():
    fake = FakeSelf()

    # create an httpx.HTTPError with a response carrying a 404 status_code
    exc = httpx.HTTPError("not found")
    exc.response = SimpleNamespace(status_code=404)

    def raise_404(method, url):
        raise exc

    fake._send_runtime_api_request = raise_404

    result = RemoteRuntime._check_existing_runtime(fake)

    assert result is False
    # should have logged that no existing runtime was found for the session id
    assert any("No existing runtime found for session ID" in m for _, m, _ in fake.log_calls)


def test_http_other_error_round_030():
    fake = FakeSelf()

    exc = httpx.HTTPError("server error")
    exc.response = SimpleNamespace(status_code=500)

    def raise_500(method, url):
        raise exc

    fake._send_runtime_api_request = raise_500

    with pytest.raises(httpx.HTTPError):
        RemoteRuntime._check_existing_runtime(fake)


def test_json_decode_error_round_030():
    fake = FakeSelf()

    response = SimpleNamespace()

    # response.json will raise a JSONDecodeError to simulate invalid JSON from API
    def bad_json():
        # construct a real JSONDecodeError
        raise json.decoder.JSONDecodeError("Expecting value", doc="", pos=0)

    response.json = bad_json

    fake._send_runtime_api_request = lambda method, url: response

    with pytest.raises(json.decoder.JSONDecodeError):
        RemoteRuntime._check_existing_runtime(fake)
