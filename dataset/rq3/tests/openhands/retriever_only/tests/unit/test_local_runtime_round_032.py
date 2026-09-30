import asyncio
import importlib
import subprocess
import tempfile
import os
import shutil
from types import SimpleNamespace

import pytest

# Import the module under test
local_runtime = importlib.import_module("openhands.runtime.impl.local.local_runtime")


def _make_fake_server(process_obj=None, temp_workspace=None):
    """Helper creating a minimal server_info-like object used by LocalRuntime.delete."""
    ev = SimpleNamespace(set_called=False)

    def set_method():
        ev.set_called = True

    ev.set = set_method

    log_thread = SimpleNamespace(join_called=False)

    def join_method(timeout=None):
        log_thread.join_called = True

    log_thread.join = join_method

    return SimpleNamespace(
        log_thread_exit_event=ev,
        process=process_obj,
        log_thread=log_thread,
        temp_workspace=temp_workspace,
    )


class _ProcRaiseTimeout:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        # Raise the exact exception the code catches
        raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)

    def kill(self):
        self.killed = True


class _ProcNormal:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        return None

    def kill(self):
        self.killed = True


@pytest.mark.parametrize("use_temp_workspace", [True, False])
def test_delete_cleans_warm_timeout_round_032(tmp_path, use_temp_workspace):
    """When deleting the last running conversation, warm servers should be cleaned up.

    This covers the branch where process.wait raises TimeoutExpired and process.kill() is called,
    as well as removal of warm server entries and shutil.rmtree for temp workspaces.
    """
    # Backup global state
    orig_running = dict(local_runtime._RUNNING_SERVERS)
    orig_warm = list(local_runtime._WARM_SERVERS)

    try:
        # Create a running server entry for conversation 'conv1' with no process
        running_server = _make_fake_server(process_obj=None, temp_workspace=None)
        local_runtime._RUNNING_SERVERS.clear()
        local_runtime._RUNNING_SERVERS["conv1"] = running_server

        # Create a warm server whose process.wait will raise TimeoutExpired
        proc = _ProcRaiseTimeout()

        temp_dir = None
        if use_temp_workspace:
            temp_dir = str(tmp_path / "workspace")
            os.makedirs(temp_dir, exist_ok=True)
            # create a sentinel file so we know rmtree removed it
            open(os.path.join(temp_dir, "x.txt"), "w").close()

        warm_server = _make_fake_server(process_obj=proc, temp_workspace=temp_dir)
        local_runtime._WARM_SERVERS.clear()
        local_runtime._WARM_SERVERS.append(warm_server)

        # Call the async delete
        asyncio.run(local_runtime.LocalRuntime.delete("conv1"))

        # Assertions for running servers removal
        assert "conv1" not in local_runtime._RUNNING_SERVERS

        # Warm server should have been removed from the list
        assert warm_server not in local_runtime._WARM_SERVERS

        # Process terminate and wait were called and kill called due to timeout
        assert proc.terminated is True
        assert proc.wait_called is True
        assert proc.killed is True

        # log thread exit event set and join called
        assert running_server.log_thread_exit_event.set_called is True
        assert warm_server.log_thread_exit_event.set_called is True
        assert warm_server.log_thread.join_called is True

        # If a temp workspace existed it should be removed
        if use_temp_workspace:
            assert not os.path.exists(temp_dir)

    finally:
        # Restore globals as best-effort
        local_runtime._RUNNING_SERVERS.clear()
        local_runtime._RUNNING_SERVERS.update(orig_running)
        local_runtime._WARM_SERVERS.clear()
        local_runtime._WARM_SERVERS.extend(orig_warm)


def test_delete_terminates_process_without_kill_round_032():
    """Covers the branch where a running server has a live process whose wait succeeds (no kill)."""
    orig_running = dict(local_runtime._RUNNING_SERVERS)
    orig_warm = list(local_runtime._WARM_SERVERS)

    try:
        # Set up a running server whose process.wait succeeds
        proc = _ProcNormal()
        running_server = _make_fake_server(process_obj=proc, temp_workspace=None)
        local_runtime._RUNNING_SERVERS.clear()
        local_runtime._RUNNING_SERVERS["conv2"] = running_server

        # Ensure there are no warm servers so the warm-clean branch is skipped
        local_runtime._WARM_SERVERS.clear()

        asyncio.run(local_runtime.LocalRuntime.delete("conv2"))

        # The running server entry is removed
        assert "conv2" not in local_runtime._RUNNING_SERVERS

        # Process terminate and wait were called, but kill was not needed
        assert proc.terminated is True
        assert proc.wait_called is True
        assert proc.killed is False

        # log thread exit and join behavior for running_server
        assert running_server.log_thread_exit_event.set_called is True
        # join was invoked in delete for the running server's log_thread
        assert running_server.log_thread.join_called is True

    finally:
        local_runtime._RUNNING_SERVERS.clear()
        local_runtime._RUNNING_SERVERS.update(orig_running)
        local_runtime._WARM_SERVERS.clear()
        local_runtime._WARM_SERVERS.extend(orig_warm)
