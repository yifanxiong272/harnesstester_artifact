import os
import threading
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

from openhands.runtime.impl.local import local_runtime

# Helpers for faking behavior
class FakeResponse:
    def raise_for_status(self):
        return None

class FakeClient:
    def __init__(self, *args, **kwargs):
        # store any kwargs for deterministic introspection if needed
        self._args = args
        self._kwargs = kwargs

    def get(self, url):
        # success response by default; tests can monkeypatch this method
        return FakeResponse()

class FakeProcessLive:
    def __init__(self):
        self.terminate_called = False
        self.kill_called = False

    def poll(self):
        # Process is alive
        return None

    def terminate(self):
        self.terminate_called = True

    def wait(self, timeout=None):
        # Successful wait (no TimeoutExpired)
        return 0

    def kill(self):
        self.kill_called = True

class FakeProcessTimeout(FakeProcessLive):
    def wait(self, timeout=None):
        # Simulate a long-running process that times out when waiting
        raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)

class FakeLogThread:
    def __init__(self):
        self.join_called = False

    def join(self, timeout=None):
        self.join_called = True

class FakeServerInfo(SimpleNamespace):
    # execution_server_port attribute added for info logging
    pass


def _patch_no_retry(monkeypatch):
    # Replace tenacity.retry with a no-op decorator so wait loops do not sleep/retry
    monkeypatch.setattr(local_runtime.tenacity, "retry", lambda *a, **k: (lambda f: f))


def test_create_warm_server_success_round_040(monkeypatch, tmp_path):
    """Successful warm server creation should append server_info to _WARM_SERVERS."""
    _patch_no_retry(monkeypatch)

    # Prepare fake server info with a live process
    process = FakeProcessLive()
    log_thread = FakeLogThread()
    server_info = FakeServerInfo(
        execution_server_port=12345,
        process=process,
        log_thread_exit_event=threading.Event(),
        log_thread=log_thread,
        temp_workspace=None,
    )

    # Patch _create_server to return our fake server_info and a deterministic api_url
    def fake_create_server(config, plugins, workspace_prefix="warm"):
        return server_info, "http://127.0.0.1:9999"

    monkeypatch.setattr(local_runtime, "_create_server", fake_create_server)
    # Patch httpx.Client to avoid real network calls
    monkeypatch.setattr(local_runtime.httpx, "Client", FakeClient)

    # Ensure warm servers list is clean
    monkeypatch.setattr(local_runtime, "_WARM_SERVERS", [], raising=False)

    # Run the function under test
    local_runtime._create_warm_server(config=None, plugins=[])

    # Assertions: server_info must have been appended
    assert server_info in local_runtime._WARM_SERVERS
    # The process should remain alive and not have termination flags set
    assert not process.terminate_called
    assert not process.kill_called
    # The log thread should not have been joined in success path
    assert not log_thread.join_called


def test_create_warm_server_cleanup_on_failure_round_040(monkeypatch, tmp_path):
    """If the warm server never becomes alive, the cleanup path should run and remove workspace."""
    _patch_no_retry(monkeypatch)

    # Create a real temp directory to validate rmtree is called with that path
    temp_workspace = tmp_path / "temp_ws"
    temp_workspace.mkdir()

    # Prepare fake server info with a process that times out on wait
    process = FakeProcessTimeout()
    log_thread = FakeLogThread()
    exit_event = threading.Event()

    server_info = FakeServerInfo(
        execution_server_port=54321,
        process=process,
        log_thread_exit_event=exit_event,
        log_thread=log_thread,
        temp_workspace=str(temp_workspace),
    )

    # _create_server returns server_info so 'server_info' is present in locals() of function
    def fake_create_server(config, plugins, workspace_prefix="warm"):
        return server_info, "http://127.0.0.1:8888"

    monkeypatch.setattr(local_runtime, "_create_server", fake_create_server)

    # Patch httpx.Client.get to raise to simulate server not ready
    class BrokenClient(FakeClient):
        def get(self, url):
            raise ConnectionError("cannot connect")

    monkeypatch.setattr(local_runtime.httpx, "Client", BrokenClient)

    # Ensure tenacity.retry is a no-op (no retries/delays)
    # Already done via _patch_no_retry

    # Capture rmtree calls without deleting real files (we can let it delete our temp dir)
    called = {}

    def fake_rmtree(path):
        called['path'] = path

    monkeypatch.setattr(local_runtime.shutil, "rmtree", fake_rmtree)

    # Ensure warm servers list is clean
    monkeypatch.setattr(local_runtime, "_WARM_SERVERS", [], raising=False)

    # Execute: function should swallow exceptions and perform cleanup
    local_runtime._create_warm_server(config=None, plugins=[])

    # Assertions verifying cleanup occurred
    assert exit_event.is_set(), "log_thread_exit_event should have been set"
    assert process.terminate_called, "Process.terminate should have been called"
    # Because wait() raises TimeoutExpired, kill() should have been called
    assert process.kill_called, "Process.kill should have been called after timeout"
    assert log_thread.join_called, "log_thread.join should have been invoked"
    # rmtree should have been invoked with the server's temp_workspace
    assert called.get('path') == str(temp_workspace)
