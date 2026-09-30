# file: openhands/runtime/builder/remote.py:35-127
# asked: {"lines": [44, 45, 46, 47, 50, 53, 54, 55, 59, 60, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 77, 79, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 98, 99, 100, 101, 104, 105, 106, 108, 109, 110, 111, 118, 119, 121, 122, 125, 127], "branches": [[59, 60], [59, 63], [72, 73], [72, 77], [86, 87], [86, 127], [87, 88], [87, 91], [98, 99], [98, 104], [108, 109], [108, 111], [111, 118], [111, 125]]}
# gained: {"lines": [44, 45, 46, 47, 50, 53, 54, 55, 59, 60, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 79, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 98, 99, 100, 101, 104, 105, 106, 108, 109, 110, 111, 118, 119, 121, 122, 125], "branches": [[59, 60], [59, 63], [72, 73], [86, 87], [87, 88], [87, 91], [98, 99], [98, 104], [108, 109], [108, 111], [111, 118], [111, 125]]}

import base64
import io
import tarfile
import types
from types import SimpleNamespace

import httpx
import pytest

from openhands.core.exceptions import AgentRuntimeBuildError
from openhands.runtime.builder.remote import RemoteRuntimeBuilder

# Helper response-like object
class Resp:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json

def make_temp_context(tmp_path):
    # create a simple directory with a file to tar
    d = tmp_path / "context"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("hello")
    return str(d)

def test_build_success_with_tags_and_sleep(monkeypatch, tmp_path):
    # Prepare context dir
    path = make_temp_context(tmp_path)

    builder = RemoteRuntimeBuilder(api_url="http://api", api_key="key")

    calls = []

    # Mock send_request to handle POST then two GETs: first PENDING, then SUCCESS
    def fake_send_request(session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == 'POST':
            return Resp(json_data={'build_id': 'b1'})
        elif method == 'GET':
            # pop count of GETs so first GET is PENDING, second is SUCCESS
            get_call_count = sum(1 for c in calls if c[0] == 'GET')
            if get_call_count == 1:
                return Resp(status_code=200, json_data={'status': 'PENDING'})
            else:
                return Resp(status_code=200, json_data={'status': 'SUCCESS', 'image': 'repo:tag'})
        raise RuntimeError("Unexpected method")

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)

    # should_continue should be True so loop runs; then still True on second iteration
    sc_calls = {'count': 0}
    def fake_should_continue():
        sc_calls['count'] += 1
        # allow loop to run multiple times
        return True
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', fake_should_continue)

    # Capture sleep_if_should_continue calls
    sleep_calls = {'called': 0}
    def fake_sleep_if_should_continue(secs):
        sleep_calls['called'] += 1
    monkeypatch.setattr('openhands.runtime.builder.remote.sleep_if_should_continue', fake_sleep_if_should_continue)

    # Run build with two tags to exercise tags appending
    result = builder.build(path, tags=['target:latest', 'other:tag'])
    assert result == 'repo:tag'

    # Verify send_request saw a POST and at least two GETs
    methods = [c[0] for c in calls]
    assert 'POST' in methods
    assert methods.count('GET') >= 2

    # Verify files sent in POST include context and tags
    post_kwargs = next(k for m, u, k in calls if m == 'POST')
    files = post_kwargs.get('files')
    assert isinstance(files, list)
    # first tuple should be context, second target_image, and third tags for additional tag
    keys = [t[0] for t in files]
    assert 'context' in keys
    assert 'target_image' in keys
    assert 'tags' in keys

    # Ensure sleep_if_should_continue was called once (from the PENDING state)
    assert sleep_calls['called'] >= 1

def test_build_rate_limited_then_success(monkeypatch, tmp_path):
    path = make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder(api_url="http://api", api_key="key")

    call_log = []

    # We will raise HTTPError with response.status_code == 429 on first POST, then succeed
    def fake_send_request(session, method, url, **kwargs):
        call_log.append((method, url))
        if method == 'POST':
            if len([c for c in call_log if c[0] == 'POST']) == 1:
                # create HTTPError instance with response.status_code == 429
                err = httpx.HTTPError("rate limited")
                err.response = types.SimpleNamespace(status_code=429)
                raise err
            else:
                return Resp(json_data={'build_id': 'b2'})
        elif method == 'GET':
            return Resp(status_code=200, json_data={'status': 'SUCCESS', 'image': 'repo:rl'})
        raise RuntimeError("Unexpected")

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)

    # Patch time.sleep used in rate-limit branch to avoid delay
    slept = {'secs': 0}
    def fake_sleep(s):
        slept['secs'] = s
    monkeypatch.setattr('openhands.runtime.builder.remote.time.sleep', fake_sleep)

    # should_continue True
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)

    result = builder.build(path, tags=['t:1'])
    assert result == 'repo:rl'
    # ensure we indeed slept 30 seconds (but via patched no-op)
    assert slept['secs'] == 30
    # ensure there were two POST attempts
    post_attempts = [c for c in call_log if c[0] == 'POST']
    assert len(post_attempts) == 2

def test_build_status_non_200_raises(monkeypatch, tmp_path):
    path = make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder(api_url="http://api", api_key="key")

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return Resp(json_data={'build_id': 'b3'})
        elif method == 'GET':
            return Resp(status_code=500, text='internal error')
        raise RuntimeError

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(path, tags=['t'])
    assert 'internal error' in str(exc.value)

@pytest.mark.parametrize("status,has_error,expected_msg_part", [
    ('FAILURE', True, 'explicit error'),
    ('CANCELLED', False, 'Build failed with status: CANCELLED'),
    ('TIMEOUT', False, 'Build failed with status: TIMEOUT'),
    ('INTERNAL_ERROR', True, 'oops'),
])
def test_build_failure_statuses_raise(monkeypatch, tmp_path, status, has_error, expected_msg_part):
    path = make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder(api_url="http://api", api_key="key")

    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return Resp(json_data={'build_id': 'b4'})
        elif method == 'GET':
            if has_error:
                return Resp(status_code=200, json_data={'status': status, 'error': 'explicit error' if status == 'FAILURE' else 'oops'})
            else:
                return Resp(status_code=200, json_data={'status': status})
        raise RuntimeError

    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(path, tags=['t'])
    assert expected_msg_part in str(exc.value)

def test_build_timeout_raises(monkeypatch, tmp_path):
    path = make_temp_context(tmp_path)
    builder = RemoteRuntimeBuilder(api_url="http://api", api_key="key")

    # POST returns build_id
    def fake_send_request(session, method, url, **kwargs):
        if method == 'POST':
            return Resp(json_data={'build_id': 'bt'})
        else:
            pytest.fail("GET should not be reached due to timeout before GET in this test")
    monkeypatch.setattr('openhands.runtime.builder.remote.send_request', fake_send_request)

    # should_continue returns True so loop enters and triggers timeout check
    monkeypatch.setattr('openhands.runtime.builder.remote.should_continue', lambda: True)

    # Patch time.time to simulate immediate timeout: first call sets start_time, second call is beyond timeout
    timeout = 30 * 60
    times = [1000.0, 1000.0 + timeout + 1.0]
    def fake_time():
        # return last value if exhausted
        return times.pop(0) if times else 10000.0
    monkeypatch.setattr('openhands.runtime.builder.remote.time.time', fake_time)

    with pytest.raises(AgentRuntimeBuildError) as exc:
        builder.build(path, tags=['t'])
    assert 'Build timed out after 30 minutes' in str(exc.value)
