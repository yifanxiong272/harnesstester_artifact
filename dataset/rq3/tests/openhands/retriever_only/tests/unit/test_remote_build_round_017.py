import base64
import io
import tarfile
import os
import tempfile
from types import SimpleNamespace
import httpx
import time
import pytest

from openhands.runtime.builder.remote import RemoteRuntimeBuilder, AgentRuntimeBuildError


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200, text=''):
        self._json = json_data or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json


def _make_temp_dir_with_file():
    d = tempfile.mkdtemp()
    # create a file so tar.add will include something
    p = os.path.join(d, 'dummy.txt')
    with open(p, 'w') as f:
        f.write('hello')
    return d


def test_build_success_with_multiple_tags_round_017(monkeypatch):
    # Prepare a temporary directory to be archived
    path = _make_temp_dir_with_file()

    # State holder for send_request calls
    calls = []

    def fake_send_request(session, method, url, **kwargs):
        calls.append({'method': method, 'url': url, 'kwargs': kwargs})
        if method == 'POST':
            return _FakeResponse(json_data={'build_id': 'build-123'})
        elif method == 'GET':
            # Immediately return success status
            return _FakeResponse(json_data={'status': 'SUCCESS', 'image': 'repo/image:latest'}, status_code=200)
        raise RuntimeError('Unexpected method')

    # should_continue returns True but the loop will exit on SUCCESS immediately
    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    # Provide a minimal session object with headers.update
    session = SimpleNamespace(headers={})
    builder = RemoteRuntimeBuilder('http://api', 'APIKEY', session=session)

    # Call build with multiple tags to exercise the tags append branch
    result = builder.build(path, ['repo/image:latest', 'repo/image:tag2'])

    # Assertions: result and that POST received tags entry for additional tag
    assert result == 'repo/image:latest'

    # Validate that the first (POST) call included files and extra tags
    post_call = next(c for c in calls if c['method'] == 'POST')
    files = post_call['kwargs'].get('files')
    # files should be a list-like and include the additional tag entry
    assert any(f[0] == 'tags' and f[1][1] == 'repo/image:tag2' for f in files), 'tags entry not found in files'


def test_build_status_non_200_raises_round_017(monkeypatch):
    path = _make_temp_dir_with_file()

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _FakeResponse(json_data={'build_id': 'b-1'})
        elif method == 'GET':
            return _FakeResponse(status_code=500, text='internal server error')
        raise RuntimeError('Unexpected method')

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    session = SimpleNamespace(headers={})
    builder = RemoteRuntimeBuilder('http://api', 'KEY', session=session)

    with pytest.raises(AgentRuntimeBuildError) as excinfo:
        builder.build(path, ['img:tag'])
    # error message should include the status response text
    assert 'internal server error' in str(excinfo.value)


def test_build_failure_status_with_error_field_round_017(monkeypatch):
    path = _make_temp_dir_with_file()

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return _FakeResponse(json_data={'build_id': 'b-2'})
        elif method == 'GET':
            return _FakeResponse(json_data={'status': 'FAILURE', 'error': 'bad things'}, status_code=200)
        raise RuntimeError('Unexpected method')

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    session = SimpleNamespace(headers={})
    builder = RemoteRuntimeBuilder('http://api', 'K', session=session)

    with pytest.raises(AgentRuntimeBuildError) as excinfo:
        builder.build(path, ['img:latest'])
    assert 'bad things' in str(excinfo.value)


def test_http_error_429_retries_round_017(monkeypatch):
    # This test ensures the 429 branch retries after sleeping and then succeeds
    path = _make_temp_dir_with_file()

    call_count = {'n': 0}

    def fake_send_request(session, method, url, **kwargs):
        # First POST attempt raises an HTTPError with response.status_code == 429
        if method == 'POST':
            call_count['n'] += 1
            if call_count['n'] == 1:
                e = httpx.HTTPError('rate limited')
                # attach a response-like object with status_code 429
                e.response = SimpleNamespace(status_code=429)
                raise e
            return _FakeResponse(json_data={'build_id': 'retry-build'})
        elif method == 'GET':
            return _FakeResponse(json_data={'status': 'SUCCESS', 'image': 'retry/image:1'}, status_code=200)
        raise RuntimeError('Unexpected method')

    slept = {'called_with': None}

    def fake_sleep(sec):
        # record and no-op to keep test fast
        slept['called_with'] = sec

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.time', time)
    monkeypatch.setattr('openhands.runtime.builder.remote.time.sleep', fake_sleep)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', lambda s: None)

    session = SimpleNamespace(headers={})
    builder = RemoteRuntimeBuilder('http://api', 'K', session=session)

    result = builder.build(path, ['repo/retry:1'])
    assert result == 'retry/image:1'
    # ensure we recorded that sleep was called with 30 seconds for rate-limit backoff
    assert slept['called_with'] == 30
