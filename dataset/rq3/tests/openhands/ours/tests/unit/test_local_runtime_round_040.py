import importlib
import types
import subprocess
from types import SimpleNamespace

import pytest


MODULE_PATH = "openhands.runtime.impl.local.local_runtime"


class DummyResponse:
    def __init__(self, raise_for_status_exc=None):
        self._exc = raise_for_status_exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc


class FakeClient:
    def __init__(self, *, timeout=None, verify=None):
        self.timeout = timeout
        self.verify = verify
        self.requested_urls = []

    def get(self, url):
        self.requested_urls.append(url)
        # Will be patched per-test by setting attribute `next_response` on the instance
        return getattr(self, "next_response")


class DummyProcess:
    def __init__(self, poll_return=None, wait_raise=None):
        # poll_return: value returned by poll(); if not None then process considered dead
        self._poll_return = poll_return
        self.wait_raise = wait_raise
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def poll(self):
        return self._poll_return

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        if self.wait_raise:
            raise self.wait_raise
        return 0

    def kill(self):
        self.killed = True


class DummyEvent:
    def __init__(self):
        self.set_called = False

    def set(self):
        self.set_called = True


class DummyThread:
    def __init__(self):
        self.join_called = False

    def join(self, timeout=None):
        self.join_called = True


@pytest.fixture(autouse=True)
def local_module(monkeypatch):
    """Import the module and patch tenacity.retry to a no-op decorator and
    ensure stop_if_should_exit returns a simple tenacity stop to avoid side effects.
    Also clear module._WARM_SERVERS before each test.
    """
    module = importlib.import_module(MODULE_PATH)

    # Make tenacity.retry a no-op decorator so the inner function is used directly
    monkeypatch.setattr(module, "tenacity", module.tenacity)

    # Patch the retry symbol on the module to be a function that ignores args and returns identity decorator
    monkeypatch.setattr(module, "tenacity", module.tenacity)

    # Replace tenacity.retry used inside _create_warm_server with identity decorator
    monkeypatch.setattr(module.tenacity, "retry", lambda *a, **k: (lambda f: f))

    # Ensure stop_if_should_exit returns a harmless tenacity stop object (avoid external side effects)
    monkeypatch.setattr(module, "stop_if_should_exit", lambda: module.tenacity.stop_after_delay(0))

    # Reset warm servers list
    monkeypatch.setattr(module, "_WARM_SERVERS", [], raising=False)

    yield module


def _make_server_info(process: DummyProcess, port: int = 12345, temp_workspace: str | None = None):
    si = SimpleNamespace()
    si.process = process
    si.execution_server_port = port
    si.log_thread_exit_event = DummyEvent()
    si.log_thread = DummyThread()
    si.temp_workspace = temp_workspace
    return si


def test_create_warm_server_success_round_040(local_module, monkeypatch):
    """When the server process is alive and /alive returns 200, the server info is appended to _WARM_SERVERS.

    This exercises the branch where poll() is None (process alive) and the GET/raise_for_status path succeeds.
    """
    module = local_module

    # Prepare a running process (poll -> None)
    proc = DummyProcess(poll_return=None)
    server_info = _make_server_info(proc, port=4242, temp_workspace=None)
    api_url = "http://127.0.0.1:4242"

    # Patch _create_server to return our objects
    def fake_create_server(config, plugins, workspace_prefix=None):
        return server_info, api_url

    monkeypatch.setattr(module, "_create_server", fake_create_server)

    # Patch httpx.Client to our FakeClient and provide a response that does not raise
    def fake_client_ctor(*, timeout, verify):
        c = FakeClient(timeout=timeout, verify=verify)
        c.next_response = DummyResponse(raise_for_status_exc=None)
        return c

    monkeypatch.setattr(module, "httpx", module.httpx)
    monkeypatch.setattr(module.httpx, "Client", fake_client_ctor)

    # Run the function under test
    module._create_warm_server(config=None, plugins=[])

    # Assertions: warm server added and client requested the /alive endpoint
    assert module._WARM_SERVERS, "_WARM_SERVERS should have one entry"
    assert module._WARM_SERVERS[-1] is server_info


def test_create_warm_server_process_died_cleanup_round_040(local_module, monkeypatch):
    """If the server process is already dead (poll() returns non-None), wait_until_alive should raise
    and the outer except should perform cleanup: set event, terminate, wait (no kill), join thread, and rmtree.
    """
    module = local_module

    # Process is dead: poll returns 1
    proc = DummyProcess(poll_return=1, wait_raise=None)
    tmpdir = "/tmp/fake_workspace_1"
    server_info = _make_server_info(proc, port=9999, temp_workspace=tmpdir)
    api_url = "http://127.0.0.1:9999"

    def fake_create_server(config, plugins, workspace_prefix=None):
        return server_info, api_url

    monkeypatch.setattr(module, "_create_server", fake_create_server)

    # Patch httpx.Client so it would not be used (we shouldn't reach GET due to poll returning non-None)
    monkeypatch.setattr(module.httpx, "Client", lambda *a, **k: FakeClient())

    # Patch shutil.rmtree to capture call
    removed = {}

    def fake_rmtree(path):
        removed['path'] = path

    monkeypatch.setattr(module, "shutil", module.shutil)
    monkeypatch.setattr(module.shutil, "rmtree", fake_rmtree)

    # Run the function which should trigger cleanup
    module._create_warm_server(config=None, plugins=[])

    # Verify cleanup actions
    assert server_info.log_thread_exit_event.set_called, "log_thread_exit_event.set() must be called"
    assert proc.terminated, "process.terminate() must be called when process exists"
    assert proc.wait_called, "process.wait() must be attempted"
    assert not proc.killed, "process.kill() should not be called in normal wait success"
    assert server_info.log_thread.join_called, "log_thread.join() must be called"
    assert removed.get('path') == tmpdir, "temp workspace must be removed via shutil.rmtree"


def test_create_warm_server_wait_timeout_kills_round_040(local_module, monkeypatch):
    """If wait(timeout=5) raises subprocess.TimeoutExpired, process.kill() must be called during cleanup.

    This test triggers the GET -> exception path so the outer except executes and the process.wait raises TimeoutExpired.
    """
    module = local_module

    # Running process (poll -> None) but GET will raise causing the outer except
    proc = DummyProcess(poll_return=None, wait_raise=subprocess.TimeoutExpired(pid=1234, timeout=5))
    tmpdir = "/tmp/fake_workspace_2"
    server_info = _make_server_info(proc, port=2222, temp_workspace=tmpdir)
    api_url = "http://127.0.0.1:2222"

    def fake_create_server(config, plugins, workspace_prefix=None):
        return server_info, api_url

    monkeypatch.setattr(module, "_create_server", fake_create_server)

    # Faulty client that raises on GET
    def fake_client_ctor(*, timeout, verify):
        c = FakeClient(timeout=timeout, verify=verify)
        # Make .get() return a response that will raise on raise_for_status
        c.next_response = DummyResponse(raise_for_status_exc=RuntimeError("not ready"))
        return c

    monkeypatch.setattr(module.httpx, "Client", fake_client_ctor)

    # Patch shutil.rmtree to a no-op and capture
    removed = {}

    def fake_rmtree(path):
        removed['path'] = path

    monkeypatch.setattr(module.shutil, "rmtree", fake_rmtree)

    # Run the function which should trigger cleanup and cause kill() due to TimeoutExpired
    module._create_warm_server(config=None, plugins=[])

    assert server_info.log_thread_exit_event.set_called, "log_thread_exit_event.set() must be called"
    assert proc.terminated, "process.terminate() should be called before waiting/killing"
    assert proc.wait_called, "process.wait() must be attempted"
    assert proc.killed, "process.kill() must be called when wait() times out"
    assert server_info.log_thread.join_called, "log_thread.join() must be called"
    assert removed.get('path') == tmpdir, "temp workspace must be removed via shutil.rmtree"
