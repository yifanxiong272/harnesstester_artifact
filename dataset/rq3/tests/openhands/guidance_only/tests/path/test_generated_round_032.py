import asyncio
import subprocess
import tempfile
import threading
import types
import shutil
import pytest

import openhands.runtime.impl.local.local_runtime as local_runtime


class FakeProcess:
    def __init__(self, wait_behavior="ok"):
        self.terminated = False
        self.killed = False
        self.wait_called = False
        self.wait_behavior = wait_behavior

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        if self.wait_behavior == "timeout":
            # raise the exact subprocess exception the code expects
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)
        return None

    def kill(self):
        self.killed = True


class FakeLogThread:
    def __init__(self):
        self.joined_timeout = None

    def join(self, timeout=None):
        # record the timeout requested
        self.joined_timeout = timeout


def _make_server_info(process_wait_behavior="ok", temp_workspace=None):
    """Return an object shaped like the runtime's server_info.

    Attributes expected by LocalRuntime.delete:
      - log_thread_exit_event: has .set()
      - process: has terminate(), wait(timeout), kill()
      - log_thread: has join(timeout)
      - temp_workspace: path or falsy
    """
    server_info = types.SimpleNamespace()
    server_info.log_thread_exit_event = threading.Event()
    server_info.process = FakeProcess(wait_behavior=process_wait_behavior)
    server_info.log_thread = FakeLogThread()
    server_info.temp_workspace = temp_workspace
    return server_info


def _reset_module_state(module):
    # Ensure global containers are clean between tests
    module._RUNNING_SERVERS.clear()
    module._WARM_SERVERS.clear()


def test_delete_running_server_round_032(tmp_path, monkeypatch):
    """When a running conversation exists, delete should signal exit, terminate and wait the process,
    join the log thread, and remove the entry from _RUNNING_SERVERS.

    This covers the branch where process.wait() returns normally.
    """
    module = local_runtime
    # Ensure a clean baseline
    _reset_module_state(module)

    conv_id = "conv-running"
    server_info = _make_server_info(process_wait_behavior="ok")

    # Place into module global as if the runtime started
    module._RUNNING_SERVERS[conv_id] = server_info

    # Run the async delete method synchronously
    asyncio.run(module.LocalRuntime.delete(conv_id))

    # Assertions (observable effects)
    assert conv_id not in module._RUNNING_SERVERS
    # The log thread should have been told to exit
    assert server_info.log_thread_exit_event.is_set() is True
    # Process termination and wait should have been invoked
    assert server_info.process.terminated is True
    assert server_info.process.wait_called is True
    # Log thread join should be called with the expected timeout
    assert server_info.log_thread.joined_timeout == 5


def test_delete_last_server_triggers_warm_cleanup_round_032(tmp_path, monkeypatch):
    """When deleting the last running conversation, warm servers should be cleaned up.

    This test covers the branch where warm server process.wait() raises TimeoutExpired,
    causing .kill() to be called, temp_workspace removal via shutil.rmtree, and removal
    from the _WARM_SERVERS list.
    """
    module = local_runtime
    # Reset any prior state
    _reset_module_state(module)

    # Prepare running server and warm server
    conv_id = "conv-last"
    running_info = _make_server_info(process_wait_behavior="ok")
    module._RUNNING_SERVERS[conv_id] = running_info

    # Create a fake temp workspace path (we will patch shutil.rmtree to avoid touching FS)
    fake_workspace = str(tmp_path / "fake_ws")

    # Warm server will simulate a process that times out on wait -> triggers kill()
    warm_info = _make_server_info(process_wait_behavior="timeout", temp_workspace=fake_workspace)

    # Put the warm server in the module-level list (copy semantics matching the source loop)
    module._WARM_SERVERS.append(warm_info)

    # Patch shutil.rmtree to record calls instead of removing real files
    removed_paths = []

    def fake_rmtree(path):
        removed_paths.append(path)

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    # Call delete for the last active conversation
    asyncio.run(module.LocalRuntime.delete(conv_id))

    # After deletion, running entry should be removed
    assert conv_id not in module._RUNNING_SERVERS

    # Warm server should have been processed: its exit event set
    assert warm_info.log_thread_exit_event.is_set() is True
    # Its process should have been terminated and then killed due to TimeoutExpired
    assert warm_info.process.terminated is True
    assert warm_info.process.wait_called is True
    assert warm_info.process.killed is True
    # join should have been invoked with timeout
    assert warm_info.log_thread.joined_timeout == 5

    # The temp workspace cleanup should have been attempted and recorded
    assert removed_paths == [fake_workspace]

    # The warm server should have been removed from the module list
    assert warm_info not in module._WARM_SERVERS

    # Restore module globals to a clean state for other tests
    _reset_module_state(module)
