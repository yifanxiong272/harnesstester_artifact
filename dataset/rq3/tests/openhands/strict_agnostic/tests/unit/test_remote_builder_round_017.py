import io
import tarfile
import httpx
import time
import pytest
from types import SimpleNamespace

from openhands.runtime.builder.remote import RemoteRuntimeBuilder


class _SimpleResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def _make_temp_context(tmp_path):
    # create a small directory to be tarred by build()
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    f = ctx / "file.txt"
    f.write_text("hello")
    return str(ctx)


def test_success_round_017(monkeypatch, tmp_path):
    """Happy-path: POST returns build_id and subsequent GET returns SUCCESS with image name."""
    ctx_path = _make_temp_context(tmp_path)

    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    # control send_request to return POST then GET
    def mock_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _SimpleResp(200, {'build_id': 'build-123'})
        elif method == 'GET':
            return _SimpleResp(200, {'status': 'SUCCESS', 'image': 'registry/image:tag'})
        raise AssertionError("Unexpected method: %s" % method)

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    # keep should_continue True so loop runs; sleep_if_should_continue should be a no-op
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    result = builder.build(ctx_path, ["registry/image:tag"], platform=None)
    assert result == 'registry/image:tag'


def test_non200_status_raises_round_017(monkeypatch, tmp_path):
    """When the status endpoint returns non-200, AgentRuntimeBuildError is raised with response text."""
    ctx_path = _make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    def mock_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _SimpleResp(200, {'build_id': 'b'})
        elif method == 'GET':
            return _SimpleResp(500, None, text='server-error')
        raise AssertionError("Unexpected method: %s" % method)

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    with pytest.raises(Exception) as excinfo:
        builder.build(ctx_path, ["t"], platform=None)
    assert 'server-error' in str(excinfo.value)


def test_failure_status_raises_round_017(monkeypatch, tmp_path):
    """When status is in FAILURE list, the error from status_data['error'] is raised."""
    ctx_path = _make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    def mock_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _SimpleResp(200, {'build_id': 'b2'})
        elif method == 'GET':
            return _SimpleResp(200, {'status': 'FAILURE', 'error': 'broken'})
        raise AssertionError("Unexpected method: %s" % method)

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    with pytest.raises(Exception) as excinfo:
        builder.build(ctx_path, ["t2"], platform=None)
    assert 'broken' in str(excinfo.value)


def test_timeout_raises_round_017(monkeypatch, tmp_path):
    """If time advanced beyond timeout before status check, a timeout error is raised."""
    ctx_path = _make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    # POST returns build_id
    def mock_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _SimpleResp(200, {'build_id': 'b-timeout'})
        # should not get here because timeout triggers first
        return _SimpleResp(200, {'status': 'SUCCESS', 'image': 'x'})

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    # make time.time() return 0 when start_time is captured, then a large value inside loop
    times = [0, 999999]

    def fake_time():
        return times.pop(0)

    monkeypatch.setattr('openhands.runtime.builder.remote.time', SimpleNamespace(time=fake_time, sleep=time.sleep))

    with pytest.raises(Exception) as excinfo:
        builder.build(ctx_path, ["t-timeout"], platform=None)
    assert 'timed out' in str(excinfo.value) or 'timed out' in str(excinfo.value).lower()


def test_rate_limit_retries_round_017(monkeypatch, tmp_path):
    """Simulate HTTPError with status 429 on first POST; builder should retry (we no-op sleep) and then succeed."""
    ctx_path = _make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    call_state = {'calls': 0}

    def mock_send_request(session, method, url, **kwargs):
        # First POST call -> raise httpx.HTTPError with response.status_code == 429
        if method == 'POST':
            call_state['calls'] += 1
            if call_state['calls'] == 1:
                e = httpx.HTTPError('rate')
                resp = SimpleNamespace(status_code=429, text='rate-limited')
                e.response = resp
                raise e
            # on retry return build id
            return _SimpleResp(200, {'build_id': 'b-after-retry'})
        elif method == 'GET':
            return _SimpleResp(200, {'status': 'SUCCESS', 'image': 'after/retry:1'})
        raise AssertionError("Unexpected method: %s" % method)

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    # ensure no real sleeping
    monkeypatch.setattr('openhands.runtime.builder.remote.time', SimpleNamespace(time=time.time, sleep=lambda s: None))
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    result = builder.build(ctx_path, ["after/retry:1"], platform=None)
    assert result == 'after/retry:1'
    # ensure we did hit the retry path
    assert call_state['calls'] >= 1


def test_http_error_non_retry_round_017(monkeypatch, tmp_path):
    """If send_request raises HTTPError with non-429 code, the error should propagate out."""
    ctx_path = _make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder("http://api.local", "key", None)

    def mock_send_request(session, method, url, **kwargs):
        if method == 'POST':
            e = httpx.HTTPError('server error')
            resp = SimpleNamespace(status_code=500, text='server')
            e.response = resp
            raise e
        raise AssertionError("Unexpected method: %s" % method)

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', mock_send_request)
    # avoid sleep/delays
    monkeypatch.setattr('openhands.runtime.builder.remote.time', SimpleNamespace(time=time.time, sleep=lambda s: None))

    with pytest.raises(httpx.HTTPError):
        builder.build(ctx_path, ["t-nonretry"], platform=None)
