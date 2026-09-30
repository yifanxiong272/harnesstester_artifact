import importlib
import subprocess
import tempfile
import os
import asyncio
import types


def _make_dummy_process(raise_timeout: bool):
    class DummyProcess:
        def __init__(self, raise_timeout):
            self.terminated = False
            self.killed = False
            self.wait_called_with = None
            self.raise_timeout = raise_timeout

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            # record the passed timeout so tests can assert it
            self.wait_called_with = timeout
            if self.raise_timeout:
                # simulate subprocess.TimeoutExpired exactly as the real one
                raise subprocess.TimeoutExpired(cmd="dummy", timeout=timeout)
            return 0

        def kill(self):
            self.killed = True

    return DummyProcess(raise_timeout)


class _DummyThread:
    def __init__(self):
        self.join_called_with = None

    def join(self, timeout=None):
        # record timeout used
        self.join_called_with = timeout


class _DummyEvent:
    def __init__(self):
        self.set_called = False

    def set(self):
        self.set_called = True


def _make_server_info(process=None, temp_workspace=None, raise_timeout=False):
    # process: if None, server has no process. If provided as True/False, create process
    proc = None
    if process is True:
        proc = _make_dummy_process(raise_timeout)
    elif isinstance(process, object) and process is not None:
        # allow passing a custom process object
        proc = process

    return types.SimpleNamespace(
        process=proc,
        log_thread=_DummyThread(),
        log_thread_exit_event=_DummyEvent(),
        temp_workspace=temp_workspace,
    )


def _restore_globals(module, saved):
    # restore dict and list originals
    module._RUNNING_SERVERS = saved["running"]
    module._WARM_SERVERS = saved["warm"]


def test_delete_running_server_timeout_round_032():
    """
    Exercise the branch where a running server process.wait raises TimeoutExpired
    and warm servers exist (one with a temp workspace that should be removed).
    Assertions are deterministic and check observable state on dummy objects and filesystem.
    """
    local = importlib.import_module("openhands.runtime.impl.local.local_runtime")

    # Save originals and replace with controlled test fixtures
    saved = {"running": getattr(local, "_RUNNING_SERVERS"), "warm": getattr(local, "_WARM_SERVERS")}
    try:
        local._RUNNING_SERVERS = {}
        local._WARM_SERVERS = []

        # Create a temp dir to act as warm server workspace that should be removed
        tmpdir = tempfile.mkdtemp(prefix="openhands_test_")
        assert os.path.isdir(tmpdir)

        # Running server: its process will raise TimeoutExpired when waited on
        running_proc = _make_dummy_process(raise_timeout=True)
        running_info = types.SimpleNamespace(
            process=running_proc,
            log_thread=_DummyThread(),
            log_thread_exit_event=_DummyEvent(),
            temp_workspace=None,
        )
        local._RUNNING_SERVERS["conv-timeout"] = running_info

        # Warm server 1: has a process that will exit normally and a temp workspace
        warm_proc = _make_dummy_process(raise_timeout=False)
        warm1 = types.SimpleNamespace(
            process=warm_proc,
            log_thread=_DummyThread(),
            log_thread_exit_event=_DummyEvent(),
            temp_workspace=tmpdir,
        )

        # Warm server 2: no process, no temp workspace (exercises the branch skipping process/rmtree)
        warm2 = types.SimpleNamespace(
            process=None,
            log_thread=_DummyThread(),
            log_thread_exit_event=_DummyEvent(),
            temp_workspace=None,
        )

        local._WARM_SERVERS.extend([warm1, warm2])

        # Call the delete coroutine synchronously
        asyncio.run(local.LocalRuntime.delete("conv-timeout"))

        # Assertions for the running server path
        assert running_info.log_thread_exit_event.set_called is True
        # join should be called with timeout=5 per implementation
        assert running_info.log_thread.join_called_with == 5
        # process.wait was called with timeout=5 and then killed due to TimeoutExpired
        assert running_proc.wait_called_with == 5
        assert running_proc.terminated is True
        assert running_proc.killed is True

        # Running server removed from the global dict
        assert "conv-timeout" not in local._RUNNING_SERVERS

        # Assertions for warm servers cleanup: both warm servers should have been processed and removed
        # warm1: its event set, its thread joined, process terminated and waited (no TimeoutExpired), temp dir removed
        assert warm1.log_thread_exit_event.set_called is True
        assert warm1.log_thread.join_called_with == 5
        # warm1.process existed and should have been terminated and waited (no kill)
        assert warm1.process.terminated is True
        assert warm1.process.wait_called_with == 5
        # temp workspace should be removed from filesystem
        assert not os.path.exists(tmpdir)

        # warm2: had no process but its thread/event should still be signaled and it should have been removed
        assert warm2.log_thread_exit_event.set_called is True
        assert warm2.log_thread.join_called_with == 5

        # The module-level warm list should be emptied by the cleanup loop
        assert local._WARM_SERVERS == []

    finally:
        # Best-effort cleanup and restore original module globals
        try:
            if os.path.exists(tmpdir):
                # remove if still present
                shutil = importlib.import_module("shutil")
                shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
        _restore_globals(local, saved)


def test_delete_cleans_warm_when_not_running_round_032():
    """
    Exercise the branch where the conversation_id is not in _RUNNING_SERVERS but _RUNNING_SERVERS is empty,
    so the warm servers cleanup loop runs. Use a warm server with no process and no temp_workspace to hit
    the branches that skip termination and rmtree.
    """
    local = importlib.import_module("openhands.runtime.impl.local.local_runtime")

    # Save originals and replace
    saved = {"running": getattr(local, "_RUNNING_SERVERS"), "warm": getattr(local, "_WARM_SERVERS")}
    try:
        local._RUNNING_SERVERS = {}
        local._WARM_SERVERS = []

        # Warm server: no process and no temp workspace
        warm = types.SimpleNamespace(
            process=None,
            log_thread=_DummyThread(),
            log_thread_exit_event=_DummyEvent(),
            temp_workspace=None,
        )
        local._WARM_SERVERS.append(warm)

        # Call delete on a conversation id that doesn't exist
        asyncio.run(local.LocalRuntime.delete("non-existent-conv"))

        # Because _RUNNING_SERVERS is empty, warm cleanup runs and the warm server should be processed and removed
        assert warm.log_thread_exit_event.set_called is True
        assert warm.log_thread.join_called_with == 5
        assert local._WARM_SERVERS == []

    finally:
        _restore_globals(local, saved)
