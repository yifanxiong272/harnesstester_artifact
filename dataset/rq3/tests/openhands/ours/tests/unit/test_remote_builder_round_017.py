import os
import tempfile
import shutil
from types import SimpleNamespace
import pytest
import httpx

import openhands.runtime.builder.remote as remote_mod
from openhands.core.exceptions import AgentRuntimeBuildError


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


class FakeSession:
    """Minimal session replacement with headers dict for constructor compatibility."""
    def __init__(self):
        self.headers = {}


def _make_temp_dir_with_file():
    td = tempfile.mkdtemp()
    fname = os.path.join(td, "f.txt")
    with open(fname, "w") as f:
        f.write("hello")
    return td


def test_build_success_with_multiple_tags_round_017(monkeypatch):
    # Prepare temporary build context
    td = _make_temp_dir_with_file()

    builder = remote_mod.RemoteRuntimeBuilder(api_url="http://api",
                                              api_key="k",
                                              session=FakeSession())

    captured = {}

    def fake_send_request(session, method, url, **kwargs):
        # capture the POST files argument for assertion
        if method == 'POST' and url.endswith('/build'):
            captured['files'] = kwargs.get('files')
            return _FakeResponse(json_data={'build_id': 'b1'})
        # status polling
        if method == 'GET' and url.endswith('/build_status'):
            return _FakeResponse(status_code=200, json_data={'status': 'SUCCESS', 'image': 'repo:latest'})
        raise RuntimeError("unexpected request")

    # Allow loop to run at least once; successful status will return immediately
    monkeypatch.setattr(remote_mod, 'send_request', fake_send_request)
    monkeypatch.setattr(remote_mod, 'should_continue', lambda: True)
    monkeypatch.setattr(remote_mod, 'sleep_if_should_continue', lambda s: None)
    monkeypatch.setattr(remote_mod.time, 'sleep', lambda s: None)

    result = builder.build(td, tags=["repo:latest", "repo:other"], platform=None)

    # cleanup
    shutil.rmtree(td)

    # Assertions: build returned image, and extra tag was attached in POST files
    assert result == 'repo:latest'
    assert 'files' in captured
    # files is a list of tuples; ensure there is an entry for the extra tag
    assert any(f[0] == 'tags' and f[1][1] == 'repo:other' for f in captured['files'])


def test_build_http_error_non429_raises_round_017(monkeypatch):
    td = _make_temp_dir_with_file()
    builder = remote_mod.RemoteRuntimeBuilder(api_url="http://api",
                                              api_key="k",
                                              session=FakeSession())

    # Create an httpx.HTTPError instance and attach a response with a non-429 status
    err = httpx.HTTPError("boom")
    err.response = SimpleNamespace(status_code=500)

    def raise_http_error(*args, **kwargs):
        raise err

    monkeypatch.setattr(remote_mod, 'send_request', raise_http_error)
    # Ensure sleep isn't actually called
    monkeypatch.setattr(remote_mod.time, 'sleep', lambda s: None)

    with pytest.raises(httpx.HTTPError):
        try:
            builder.build(td, tags=["repo:only"], platform=None)
        finally:
            shutil.rmtree(td)


def test_build_timeout_raises_round_017(monkeypatch):
    td = _make_temp_dir_with_file()
    builder = remote_mod.RemoteRuntimeBuilder(api_url="http://api",
                                              api_key="k",
                                              session=FakeSession())

    # First POST returns build_id
    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST' and url.endswith('/build'):
            return _FakeResponse(json_data={'build_id': 'b2'})
        # Should not reach GET because we will force timeout
        return _FakeResponse(status_code=200, json_data={'status': 'SUCCESS', 'image': 'x'})

    monkeypatch.setattr(remote_mod, 'send_request', fake_send_request)

    # should_continue allows loop
    monkeypatch.setattr(remote_mod, 'should_continue', lambda: True)
    monkeypatch.setattr(remote_mod, 'sleep_if_should_continue', lambda s: None)

    # Patch time.time to return start_time=0 then a value greater than timeout
    calls = {'n': 0}
    timeout_val = 30 * 60

    def fake_time():
        calls['n'] += 1
        if calls['n'] == 1:
            return 0.0
        return float(timeout_val + 1)

    monkeypatch.setattr(remote_mod.time, 'time', fake_time)
    monkeypatch.setattr(remote_mod.time, 'sleep', lambda s: None)

    with pytest.raises(AgentRuntimeBuildError) as excinfo:
        try:
            builder.build(td, tags=["repo:t"], platform=None)
        finally:
            shutil.rmtree(td)

    assert 'Build timed out' in str(excinfo.value)


def test_build_status_non200_raises_round_017(monkeypatch):
    td = _make_temp_dir_with_file()
    builder = remote_mod.RemoteRuntimeBuilder(api_url="http://api",
                                              api_key="k",
                                              session=FakeSession())

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST' and url.endswith('/build'):
            return _FakeResponse(json_data={'build_id': 'b3'})
        if method == 'GET' and url.endswith('/build_status'):
            return _FakeResponse(status_code=500, json_data={}, text='server error')
        raise RuntimeError("unexpected")

    monkeypatch.setattr(remote_mod, 'send_request', fake_send_request)
    monkeypatch.setattr(remote_mod, 'should_continue', lambda: True)
    monkeypatch.setattr(remote_mod, 'sleep_if_should_continue', lambda s: None)
    monkeypatch.setattr(remote_mod.time, 'sleep', lambda s: None)

    with pytest.raises(AgentRuntimeBuildError) as excinfo:
        try:
            builder.build(td, tags=["repo:e"], platform=None)
        finally:
            shutil.rmtree(td)

    assert 'server error' in str(excinfo.value)


def test_build_failure_status_with_error_message_round_017(monkeypatch):
    td = _make_temp_dir_with_file()
    builder = remote_mod.RemoteRuntimeBuilder(api_url="http://api",
                                              api_key="k",
                                              session=FakeSession())

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST' and url.endswith('/build'):
            return _FakeResponse(json_data={'build_id': 'b4'})
        if method == 'GET' and url.endswith('/build_status'):
            return _FakeResponse(status_code=200, json_data={'status': 'FAILURE', 'error': 'bad stuff'})
        raise RuntimeError("unexpected")

    monkeypatch.setattr(remote_mod, 'send_request', fake_send_request)
    monkeypatch.setattr(remote_mod, 'should_continue', lambda: True)
    monkeypatch.setattr(remote_mod, 'sleep_if_should_continue', lambda s: None)
    monkeypatch.setattr(remote_mod.time, 'sleep', lambda s: None)

    with pytest.raises(AgentRuntimeBuildError) as excinfo:
        try:
            builder.build(td, tags=["repo:f"], platform=None)
        finally:
            shutil.rmtree(td)

    assert 'bad stuff' in str(excinfo.value)
