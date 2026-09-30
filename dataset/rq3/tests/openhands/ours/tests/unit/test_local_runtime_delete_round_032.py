import asyncio
import importlib
import types
import subprocess

import pytest

# Load the module under test
local_runtime = importlib.import_module("openhands.runtime.impl.local.local_runtime")


class DummyProcess:
    def __init__(self, wait_raises=False, wait_success=True):
        self.terminated = False
        self.killed = False
        self.wait_called = False
        self._wait_raises = wait_raises
        self._wait_success = wait_success

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        if self._wait_raises:
            # raise the same exception type used in the source
            raise subprocess.TimeoutExpired(cmd="dummy", timeout=timeout)
        return 0 if self._wait_success else None

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


class DummyServerInfo:
    def __init__(self, process=None, temp_workspace=None):
        self.log_thread_exit_event = DummyEvent()
        self.process = process
        self.log_thread = DummyThread()
        self.temp_workspace = temp_workspace


@pytest.fixture(autouse=True)
def isolate_globals(monkeypatch):
    """Ensure tests run with controlled module globals and restore after."""
    # Provide fresh empty globals for each test
    monkeypatch.setattr(local_runtime, "_RUNNING_SERVERS", {}, raising=False)
    monkeypatch.setattr(local_runtime, "_WARM_SERVERS", [], raising=False)
    yield


def test_delete_removes_running_and_cleans_warm_without_process_round_032(monkeypatch):
    """When the running server has no process and warm server has no temp_workspace,
    log thread/event callbacks are invoked and both collections are cleaned.
    """
    convo_id = "conv-1"

    # Running server: no process
    running_srv = DummyServerInfo(process=None, temp_workspace=None)

    # Warm server: also no process and no temp_workspace
    warm_srv = DummyServerInfo(process=None, temp_workspace=None)

    # Put them into module globals
    local_runtime._RUNNING_SERVERS[convo_id] = running_srv
    local_runtime._WARM_SERVERS.append(warm_srv)

    # Patch shutil.rmtree to ensure it's not called (should not be called when temp_workspace is None)
    rmtree_calls = []

    def fake_rmtree(path):
        rmtree_calls.append(path)

    monkeypatch.setattr(local_runtime, "shutil", local_runtime.shutil)
    monkeypatch.setattr(local_runtime.shutil, "rmtree", fake_rmtree)

    # Call the async classmethod
    asyncio.run(local_runtime.LocalRuntime.delete(convo_id))

    # Assertions: running conversation removed
    assert convo_id not in local_runtime._RUNNING_SERVERS

    # Event set and log thread joined for running server
    assert running_srv.log_thread_exit_event.set_called is True
    assert running_srv.log_thread.join_called is True

    # Warm server event set and thread joined and removed from list
    assert warm_srv.log_thread_exit_event.set_called is True
    assert warm_srv.log_thread.join_called is True
    assert warm_srv not in local_runtime._WARM_SERVERS

    # rmtree should not have been called (temp_workspace was None)
    assert rmtree_calls == []


def test_delete_handles_process_timeout_and_cleans_temp_workspace_round_032(monkeypatch):
    """When server/process wait raises TimeoutExpired, kill() is called and
    warm servers with temp_workspace have rmtree invoked and are removed.
    """
    convo_id = "conv-2"

    # Running server: process that will raise TimeoutExpired on wait
    proc = DummyProcess(wait_raises=True)
    running_srv = DummyServerInfo(process=proc, temp_workspace=None)

    # Warm server: process that also will raise TimeoutExpired and has a temp_workspace
    warm_proc = DummyProcess(wait_raises=True)
    tmp_path = "/tmp/fake-warm-workspace"
    warm_srv = DummyServerInfo(process=warm_proc, temp_workspace=tmp_path)

    # Put them into module globals
    local_runtime._RUNNING_SERVERS[convo_id] = running_srv
    local_runtime._WARM_SERVERS.append(warm_srv)

    # Capture rmtree calls
    rmtree_calls = []

    def fake_rmtree(path):
        rmtree_calls.append(path)

    # Patch shutil.rmtree to avoid touching filesystem
    monkeypatch.setattr(local_runtime, "shutil", local_runtime.shutil)
    monkeypatch.setattr(local_runtime.shutil, "rmtree", fake_rmtree)

    # Call the async classmethod
    asyncio.run(local_runtime.LocalRuntime.delete(convo_id))

    # Running server: terminate called, wait attempted, then kill should have been called
    assert running_srv.process.terminated is True
    assert running_srv.process.wait_called is True
    assert running_srv.process.killed is True

    # Warm server: same treatment
    assert warm_srv.log_thread_exit_event.set_called is True
    assert warm_srv.log_thread.join_called is True
    assert warm_srv.process.terminated is True
    assert warm_srv.process.wait_called is True
    assert warm_srv.process.killed is True

    # rmtree should have been called for the warm server's temp_workspace
    assert rmtree_calls == [tmp_path]

    # Warm server removed from list
    assert warm_srv not in local_runtime._WARM_SERVERS

    # Running conversation removed
    assert convo_id not in local_runtime._RUNNING_SERVERS
