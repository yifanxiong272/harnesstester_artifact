# file: openhands/runtime/builder/remote.py:35-127
# asked: {"lines": [44, 45, 46, 47, 50, 53, 54, 55, 59, 60, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 77, 79, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 98, 99, 100, 101, 104, 105, 106, 108, 109, 110, 111, 118, 119, 121, 122, 125, 127], "branches": [[59, 60], [59, 63], [72, 73], [72, 77], [86, 87], [86, 127], [87, 88], [87, 91], [98, 99], [98, 104], [108, 109], [108, 111], [111, 118], [111, 125]]}
# gained: {"lines": [44, 45, 46, 47, 50, 53, 54, 55, 59, 60, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 79, 80, 81, 84, 85, 86, 87, 91, 92, 93, 94, 95, 98, 99, 100, 101, 104, 105, 106, 108, 109, 110, 111, 118, 119, 121, 122, 127], "branches": [[59, 60], [59, 63], [72, 73], [86, 87], [86, 127], [87, 91], [98, 99], [98, 104], [108, 109], [108, 111], [111, 118]]}

import base64
import io
import tarfile
import time
import types

import pytest
import httpx

from types import SimpleNamespace

from openhands.runtime.builder.remote import RemoteRuntimeBuilder
from openhands.core.exceptions import AgentRuntimeBuildError


class _MockResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def _create_test_context(tmp_path):
    d = tmp_path / "ctx"
    d.mkdir()
    (d / "file.txt").write_text("hello")
    return str(d)


def test_build_success_creates_tar_and_posts_and_returns_image(tmp_path, monkeypatch):
    # Prepare context
    ctx = _create_test_context(tmp_path)

    # Capture files passed to send_request
    captured = {}

    def fake_send_request(session, method, url, files=None, timeout=None, params=None):
        # POST to /build
        if method == 'POST' and url.endswith('/build'):
            captured['files'] = files
            return _MockResponse(json_data={'build_id': 'b1'})
        # GET to /build_status
        if method == 'GET' and url.endswith('/build_status'):
            assert params == {'build_id': 'b1'}
            return _MockResponse(status_code=200, json_data={'status': 'SUCCESS', 'image': 'img:tag'})
        raise AssertionError("Unexpected request")

    # Ensure loop runs at least once
    monkeypatch.setattr("openhands.runtime.builder.remote.send_request", fake_send_request)
    monkeypatch.setattr("openhands.runtime.builder.remote.should_continue", lambda: True)
    monkeypatch.setattr("openhands.runtime.builder.remote.sleep_if_should_continue", lambda s: None)

    builder = RemoteRuntimeBuilder("http://api", "key", session=SimpleNamespace(headers={}))

    result = builder.build(ctx, tags=['target:latest', 'target:other'])
    assert result == 'img:tag'

    # Inspect captured files: context should be base64 tar.gz
    files = captured.get('files')
    assert files is not None
    # Find the context tuple
    context_entries = [f for f in files if f[0] == 'context']
    assert len(context_entries) == 1
    _, context_tuple = context_entries[0]
    assert context_tuple[0] == 'context.tar.gz'
    b64data = context_tuple[1]
    raw = base64.b64decode(b64data)
    # Gzip header bytes
    assert raw[:2] == b'\x1f\x8b'
    # Ensure tags included
    target_entries = [f for f in files if f[0] == 'target_image']
    assert len(target_entries) == 1
    assert target_entries[0][1][1] == 'target:latest'
    tag_entries = [f for f in files if f[0] == 'tags']
    assert any(e[1][1] == 'target:other' for e in tag_entries)


def test_http_error_429_causes_retry_and_sleep_called(tmp_path, monkeypatch):
    ctx = _create_test_context(tmp_path)

    calls = {'post': 0, 'sleep_args': None}

    def fake_send_request(session, method, url, files=None, timeout=None, params=None):
        if method == 'POST' and url.endswith('/build'):
            calls['post'] += 1
            if calls['post'] == 1:
                # raise HTTPError with response.status_code == 429
                e = httpx.HTTPError("rate limited")
                e.response = SimpleNamespace(status_code=429)
                raise e
            return _MockResponse(json_data={'build_id': 'b_retry'})
        if method == 'GET' and url.endswith('/build_status'):
            return _MockResponse(status_code=200, json_data={'status': 'SUCCESS', 'image': 'img:retry'})
        raise AssertionError("Unexpected request")

    def fake_sleep(s):
        calls['sleep_args'] = s
        # Do not actually sleep

    monkeypatch.setattr("openhands.runtime.builder.remote.send_request", fake_send_request)
    monkeypatch.setattr("openhands.runtime.builder.remote.time.sleep", fake_sleep)
    monkeypatch.setattr("openhands.runtime.builder.remote.should_continue", lambda: True)
    monkeypatch.setattr("openhands.runtime.builder.remote.sleep_if_should_continue", lambda s: None)

    builder = RemoteRuntimeBuilder("http://api", "key", session=SimpleNamespace(headers={}))

    result = builder.build(ctx, tags=['t:1'])
    assert result == 'img:retry'
    assert calls['post'] == 2
    assert calls['sleep_args'] == 30


def test_status_code_not_200_raises_agent_runtime_build_error(tmp_path, monkeypatch):
    ctx = _create_test_context(tmp_path)

    def fake_send_request(session, method, url, files=None, timeout=None, params=None):
        if method == 'POST' and url.endswith('/build'):
            return _MockResponse(json_data={'build_id': 'b2'})
        if method == 'GET' and url.endswith('/build_status'):
            return _MockResponse(status_code=500, json_data=None, text='server oops')
        raise AssertionError("Unexpected request")

    monkeypatch.setattr("openhands.runtime.builder.remote.send_request", fake_send_request)
    monkeypatch.setattr("openhands.runtime.builder.remote.should_continue", lambda: True)
    monkeypatch.setattr("openhands.runtime.builder.remote.sleep_if_should_continue", lambda s: None)

    builder = RemoteRuntimeBuilder("http://api", "key", session=SimpleNamespace(headers={}))

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(ctx, tags=['t:2'])
    assert 'server oops' in str(exc.value)


def test_failure_status_without_error_uses_build_id_in_exception(tmp_path, monkeypatch):
    ctx = _create_test_context(tmp_path)

    def fake_send_request(session, method, url, files=None, timeout=None, params=None):
        if method == 'POST' and url.endswith('/build'):
            return _MockResponse(json_data={'build_id': 'b3'})
        if method == 'GET' and url.endswith('/build_status'):
            return _MockResponse(status_code=200, json_data={'status': 'FAILURE'})
        raise AssertionError("Unexpected request")

    monkeypatch.setattr("openhands.runtime.builder.remote.send_request", fake_send_request)
    monkeypatch.setattr("openhands.runtime.builder.remote.should_continue", lambda: True)
    monkeypatch.setattr("openhands.runtime.builder.remote.sleep_if_should_continue", lambda s: None)

    builder = RemoteRuntimeBuilder("http://api", "key", session=SimpleNamespace(headers={}))

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(ctx, tags=['t:3'])
    assert 'b3' in str(exc.value)


def test_build_interrupted_when_should_continue_false(tmp_path, monkeypatch):
    ctx = _create_test_context(tmp_path)

    def fake_send_request(session, method, url, files=None, timeout=None, params=None):
        if method == 'POST' and url.endswith('/build'):
            return _MockResponse(json_data={'build_id': 'b4'})
        # GET should not be called because should_continue is False
        raise AssertionError("GET should not be called")

    monkeypatch.setattr("openhands.runtime.builder.remote.send_request", fake_send_request)
    monkeypatch.setattr("openhands.runtime.builder.remote.should_continue", lambda: False)
    monkeypatch.setattr("openhands.runtime.builder.remote.sleep_if_should_continue", lambda s: None)

    builder = RemoteRuntimeBuilder("http://api", "key", session=SimpleNamespace(headers={}))

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(ctx, tags=['t:4'])
    assert 'Build interrupted' in str(exc.value)
