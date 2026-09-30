import importlib
import threading
import subprocess
import tempfile
import os
import types

import pytest

# Import the module under test
lr = importlib.import_module("openhands.runtime.impl.local.local_runtime")

# Helpers used by tests
class DummyProcess:
    def __init__(self, poll_return=None, wait_raises=False):
        # poll_return: value returned by poll(); None means running
        self._poll_return = poll_return
        self._wait_raises = wait_raises
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def poll(self):
        return self._poll_return

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        if self._wait_raises:
            raise subprocess.TimeoutExpired(cmd="dummy", timeout=timeout)
        return 0

    def kill(self):
        self.killed = True


class DummyThread:
    def __init__(self):
        self.joined_with = None

    def join(self, timeout=None):
        self.joined_with = timeout


class DummyResponse:
    def raise_for_status(self):
        return None


# Test: successful warm server becomes ready and is appended to _WARM_SERVERS
def test_success_warm_server_round_040(monkeypatch, tmp_path):
    # Arrange: clear global warm servers
    lr._WARM_SERVERS.clear()

    # Create a fake server_info
    process = DummyProcess(poll_return=None, wait_raises=False)
    server_info = types.SimpleNamespace()
    server_info.process = process
    server_info.execution_server_port = 12345
    server_info.log_thread_exit_event = threading.Event()
    server_info.log_thread = DummyThread()
    # No temp_workspace to avoid rmtree path in this test
    server_info.temp_workspace = None

    # Monkeypatch _create_server to return our fake info and api url
    def fake_create_server(config, plugins, workspace_prefix="warm"):
        return server_info, "http://localhost:12345"

    monkeypatch.setattr(lr, "_create_server", fake_create_server)

    # Monkeypatch tenacity.retry to a no-op decorator so wait_until_alive runs directly
    monkeypatch.setattr(lr.tenacity, "retry", lambda *args, **kwargs: (lambda f: f))

    # Monkeypatch httpx.Client to return an object whose get() returns a response
    class ClientOK:
        def __init__(self, timeout, verify):
            self.timeout = timeout
            self.verify = verify
            self.got = []

        def get(self, url):
            self.got.append(url)
            return DummyResponse()

    monkeypatch.setattr(lr.httpx, "Client", ClientOK)

    # Act
    lr._create_warm_server(config=None, plugins=[])

    # Assert: server_info appended and port referenced
    assert lr._WARM_SERVERS, "_WARM_SERVERS should have new server_info"
    assert lr._WARM_SERVERS[-1] is server_info
    assert server_info.execution_server_port == 12345


# Test: when wait_until_alive raises, cleanup path runs; test both wait() raising -> kill path and rmtree called
def test_cleanup_kill_timeout_round_040(monkeypatch, tmp_path):
    # Arrange: ensure warm servers cleared
    lr._WARM_SERVERS.clear()

    # Create temporary workspace directory to ensure rmtree called with a real path
    temp_dir = tmp_path / "temp_workspace"
    temp_dir.mkdir()

    # Create fake server_info with process.wait raising TimeoutExpired
    process = DummyProcess(poll_return=None, wait_raises=True)
    server_info = types.SimpleNamespace()
    server_info.process = process
    server_info.execution_server_port = 22222
    server_info.log_thread_exit_event = threading.Event()
    server_info.log_thread = DummyThread()
    server_info.temp_workspace = str(temp_dir)

    # Track calls to rmtree
    removed = []

    def fake_rmtree(path):
        # record path and simulate removal
        removed.append(path)
        # actually remove to keep environment clean
        if os.path.exists(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except Exception:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except Exception:
                        pass
            try:
                os.rmdir(path)
            except Exception:
                pass

    # _create_server returns server_info and api url
    def fake_create_server(config, plugins, workspace_prefix="warm"):
        return server_info, "http://localhost:22222"

    monkeypatch.setattr(lr, "_create_server", fake_create_server)

    # tenacity.retry no-op so our wait_until_alive executes and will raise via the client
    monkeypatch.setattr(lr.tenacity, "retry", lambda *args, **kwargs: (lambda f: f))

    # Client that always raises on get to force top-level exception and trigger cleanup
    class ClientFail:
        def __init__(self, timeout, verify):
            pass

        def get(self, url):
            raise Exception("simulated connection failure")

    monkeypatch.setattr(lr.httpx, "Client", ClientFail)

    # Patch shutil.rmtree in the module under test
    monkeypatch.setattr(lr, "shutil", types.SimpleNamespace(rmtree=fake_rmtree))

    # Act: call function; it should catch internal exception and perform cleanup without re-raising
    lr._create_warm_server(config=None, plugins=[])

    # Assert: cleanup actions happened
    assert server_info.log_thread_exit_event.is_set() is True
    # process.terminate() should have been called
    assert process.terminated is True, "process.terminate should have been called in cleanup"
    # process.wait was called and raised, causing kill to be invoked
    assert process.wait_called is True
    assert process.killed is True, "process.kill should be called after wait timeout"
    # thread join should be invoked with timeout parameter
    assert server_info.log_thread.joined_with == 5
    # rmtree should have been invoked for the temp workspace
    assert removed and removed[0] == str(temp_dir)
