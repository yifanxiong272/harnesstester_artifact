import threading
import subprocess
import types

import pytest

from openhands.runtime.impl.local import local_runtime as lr


class DummyResponse:
    def __init__(self, raise_exc=None):
        self._raise_exc = raise_exc
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if self._raise_exc:
            raise self._raise_exc


class DummySession:
    def __init__(self, behavior):
        # behavior: dict with 'url'->either DummyResponse or Exception to raise
        self.behavior = behavior
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        action = self.behavior.get(url)
        if isinstance(action, Exception):
            raise action
        return action


class DummyProcess:
    def __init__(self, poll_return=None, wait_side_effect=None):
        self._poll = poll_return
        self._wait_side_effect = wait_side_effect
        self.terminated = False
        self.killed = False

    def poll(self):
        return self._poll

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if isinstance(self._wait_side_effect, Exception):
            raise self._wait_side_effect
        return None

    def kill(self):
        self.killed = True


class DummyLogThread:
    def __init__(self):
        self.join_called = False

    def join(self, timeout=None):
        self.join_called = True


class DummyServerInfo:
    def __init__(self, process, temp_workspace=None):
        self.process = process
        self.execution_server_port = 12345
        # simple threading.Event-like with set recorded
        self.log_thread_exit_event = types.SimpleNamespace(set_called=False)

        def set_event():
            self.log_thread_exit_event.set_called = True

        self.log_thread_exit_event.set = set_event
        self.log_thread = DummyLogThread()
        self.temp_workspace = temp_workspace


@pytest.fixture(autouse=True)
def isolate_warm_servers(monkeypatch, tmp_path):
    """Ensure _WARM_SERVERS is isolated per test and patch tenacity.retry to noop.
    Also provide access to a tmp dir for temp_workspace creation.
    """
    # isolate global list
    original = list(lr._WARM_SERVERS)
    lr._WARM_SERVERS.clear()

    # Provide a fake tenacity namespace that includes the attributes used by the code
    class _FakeStop:
        def __or__(self, other):
            return self

    fake_tenacity = types.SimpleNamespace(
        retry=lambda *a, **k: (lambda f: f),
        wait_fixed=lambda t: object(),
        stop_after_delay=lambda t: _FakeStop(),
    )
    monkeypatch.setattr(lr, "tenacity", fake_tenacity)

    yield tmp_path

    # restore
    lr._WARM_SERVERS.clear()
    lr._WARM_SERVERS.extend(original)


def test_successful_warm_server_round_040(isolate_warm_servers, monkeypatch):
    """When server responds alive, _create_warm_server should append server_info to _WARM_SERVERS.

    Oracle:
    - server_info appended to lr._WARM_SERVERS
    - session.get called with the '/alive' path
    - response.raise_for_status was invoked
    """
    tmp_path = isolate_warm_servers

    # Prepare server_info with a process that is alive (poll() -> None)
    proc = DummyProcess(poll_return=None)
    server_info = DummyServerInfo(proc, temp_workspace=str(tmp_path / "ws"))

    # stub _create_server to return our server_info and api_url
    def fake_create_server(config, plugins, workspace_prefix):
        return server_info, "http://127.0.0.1:9000"

    monkeypatch.setattr(lr, "_create_server", fake_create_server)

    # stub httpx.Client to return a session that returns a successful response
    response = DummyResponse(raise_exc=None)
    session = DummySession({"http://127.0.0.1:9000/alive": response})

    class FakeClient:
        def __init__(self, timeout=None, verify=None):
            pass

        def get(self, url):
            return session.get(url)

    # Monkeypatch lr.httpx.Client to return our FakeClient instance
    monkeypatch.setattr(lr, "httpx", types.SimpleNamespace(Client=lambda *a, **k: FakeClient()))

    # Run the function under test
    lr._create_warm_server(config=None, plugins=[])

    # Assertions: server_info appended
    assert server_info in lr._WARM_SERVERS
    # session.get must have been called with '/alive'
    assert session.calls == ["http://127.0.0.1:9000/alive"]
    # response.raise_for_status should have been invoked
    assert response.raise_called is True


def test_cleanup_on_wait_failure_round_040(isolate_warm_servers, monkeypatch, tmp_path):
    """When the warm server is not yet alive (session.get raises), _create_warm_server should
    enter the except block and perform resource cleanup.

    Oracle:
    - server_info.log_thread_exit_event.set() is called
    - process.terminate() is called
    - process.wait raises subprocess.TimeoutExpired and process.kill() is called
    - log_thread.join(timeout=5) is invoked
    - shutil.rmtree called on temp_workspace
    """
    # Create a temp workspace dir to be removed
    workspace = tmp_path / "ws_to_remove"
    workspace.mkdir()

    # process.poll returns None (so not dead), but session.get will raise -> triggers except
    proc = DummyProcess(poll_return=None, wait_side_effect=subprocess.TimeoutExpired(cmd="p", timeout=5))
    server_info = DummyServerInfo(proc, temp_workspace=str(workspace))

    # stub _create_server to return server_info and api_url
    def fake_create_server(config, plugins, workspace_prefix):
        return server_info, "http://127.0.0.1:9911"

    monkeypatch.setattr(lr, "_create_server", fake_create_server)

    # stub httpx.Client such that session.get raises an exception to exercise wait_until_alive except
    class FakeClient2:
        def __init__(self, timeout=None, verify=None):
            pass

        def get(self, url):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(lr, "httpx", types.SimpleNamespace(Client=lambda *a, **k: FakeClient2()))

    # Capture shutil.rmtree calls
    removed = {}

    def fake_rmtree(path):
        removed['path'] = path

    monkeypatch.setattr(lr, "shutil", types.SimpleNamespace(rmtree=fake_rmtree))

    # Run the function under test
    lr._create_warm_server(config=None, plugins=[])

    # Assertions about cleanup
    # log_thread_exit_event.set should have been called
    assert getattr(server_info.log_thread_exit_event, "set_called", False) is True
    # process.terminate should have been called
    assert proc.terminated is True
    # process.wait side-effect should have occurred and then kill called
    assert proc.killed is True
    # log_thread.join() should have been attempted
    assert server_info.log_thread.join_called is True
    # temp_workspace should have been removed via our fake rmtree
    assert removed.get('path') == str(workspace)
