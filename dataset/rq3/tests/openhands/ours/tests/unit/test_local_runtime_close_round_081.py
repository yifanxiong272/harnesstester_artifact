import subprocess
import types
import importlib

import pytest

# Import the module under test
import openhands.runtime.impl.local.local_runtime as local_runtime


class _DummyEvent:
    def __init__(self):
        self.set_called = False

    def set(self):
        self.set_called = True


class _DummyThread:
    def __init__(self):
        self.join_called = False
        self.join_timeout = None

    def join(self, timeout=None):
        self.join_called = True
        self.join_timeout = timeout


class _DummyProcSuccess:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout):
        self.wait_called = True
        return 0

    def kill(self):
        self.killed = True


class _DummyProcTimeout(_DummyProcSuccess):
    def wait(self, timeout):
        self.wait_called = True
        raise subprocess.TimeoutExpired(cmd="cmd", timeout=timeout)


def _make_runtime_instance():
    # Create instance without calling __init__ to avoid heavy setup
    rt = object.__new__(local_runtime.LocalRuntime)
    return rt


def test_close_attach_to_existing_round_081():
    rt = _make_runtime_instance()

    # Prepare state for attach_to_existing branch
    rt.attach_to_existing = True
    rt.sid = "session-attach"
    rt.server_process = _DummyProcSuccess()
    # provide a simple log function to capture messages
    def fake_log(level, msg):
        rt._last_log = (level, msg)
    rt.log = fake_log

    # Patch the parent class close so we can observe it's called without needing the real parent
    parent_close_orig = local_runtime.ActionExecutionClient.close

    def fake_parent_close(self):
        # Record that super().close() was invoked
        self._super_closed = True

    local_runtime.ActionExecutionClient.close = fake_parent_close

    try:
        rt._super_closed = False
        rt.close()

        # Oracle assertions
        # server_process should be cleared in attach_to_existing branch
        assert rt.server_process is None
        # parent close should have been called
        assert getattr(rt, "_super_closed", False) is True
        # our fake log should have been called with info and mention the session id
        assert hasattr(rt, "_last_log")
        level, msg = rt._last_log
        assert level == "info"
        assert rt.sid in msg
    finally:
        # restore original parent close
        local_runtime.ActionExecutionClient.close = parent_close_orig


def test_close_remove_running_server_and_cleanup_successful_wait_round_081():
    rt = _make_runtime_instance()

    # Setup for non-attach path
    rt.attach_to_existing = False
    rt.sid = "running-sid"

    # Prepare a global running servers dict and ensure our sid is present
    running_orig = getattr(local_runtime, "_RUNNING_SERVERS", None)
    local_runtime._RUNNING_SERVERS = {rt.sid: "some-value"}

    # Provide a log thread exit event object with set()
    rt._log_thread_exit_event = _DummyEvent()

    # Provide a server process that returns immediately from wait()
    proc = _DummyProcSuccess()
    rt.server_process = proc

    # Provide a thread object to be joined
    rt._log_thread = _DummyThread()

    # Provide a fake temp workspace path
    rt._temp_workspace = "/tmp/fake-workspace-081"

    # Patch shutil.rmtree to capture calls
    shutil_rmtree_orig = local_runtime.shutil.rmtree
    called = {}

    def fake_rmtree(path):
        called["path"] = path

    local_runtime.shutil.rmtree = fake_rmtree

    # Patch parent close to observe final call
    parent_close_orig = local_runtime.ActionExecutionClient.close

    def fake_parent_close(self):
        self._super_closed = True

    local_runtime.ActionExecutionClient.close = fake_parent_close

    try:
        rt._super_closed = False
        rt.close()

        # Oracle assertions
        # The log thread exit event should have been signalled
        assert rt._log_thread_exit_event.set_called is True

        # The running servers entry for our sid should have been removed
        assert rt.sid not in local_runtime._RUNNING_SERVERS

        # server_process should be cleared after successful wait
        assert rt.server_process is None
        assert proc.terminated is True
        assert proc.wait_called is True
        assert proc.killed is False

        # The log thread should have been joined with a timeout
        assert rt._log_thread.join_called is True
        # Ensure join used the expected timeout (according to implementation: timeout=5)
        assert rt._log_thread.join_timeout == 5

        # rmtree should have been called and temp workspace cleared
        assert called.get("path") == "/tmp/fake-workspace-081"
        assert rt._temp_workspace is None

        # parent close should have been called
        assert getattr(rt, "_super_closed", False) is True
    finally:
        # Restore patched symbols
        local_runtime.shutil.rmtree = shutil_rmtree_orig
        local_runtime.ActionExecutionClient.close = parent_close_orig
        if running_orig is None:
            delattr(local_runtime, "_RUNNING_SERVERS")
        else:
            local_runtime._RUNNING_SERVERS = running_orig


def test_close_server_wait_timeout_and_kill_round_081():
    rt = _make_runtime_instance()

    rt.attach_to_existing = False
    rt.sid = "timeout-sid"

    # Prepare running servers
    running_orig = getattr(local_runtime, "_RUNNING_SERVERS", None)
    local_runtime._RUNNING_SERVERS = {rt.sid: "x"}

    rt._log_thread_exit_event = _DummyEvent()

    # Provide a server process that raises TimeoutExpired on wait()
    proc = _DummyProcTimeout()
    rt.server_process = proc

    rt._log_thread = _DummyThread()

    rt._temp_workspace = "/tmp/fake-timeout-081"

    # Patch shutil.rmtree to capture calls
    shutil_rmtree_orig = local_runtime.shutil.rmtree
    called = {}

    def fake_rmtree(path):
        called["path"] = path

    local_runtime.shutil.rmtree = fake_rmtree

    # Patch parent close
    parent_close_orig = local_runtime.ActionExecutionClient.close

    def fake_parent_close(self):
        self._super_closed = True

    local_runtime.ActionExecutionClient.close = fake_parent_close

    try:
        rt._super_closed = False
        rt.close()

        # Oracle assertions for timeout branch
        # Terminate should have been called before wait
        assert proc.terminated is True
        # wait should have been attempted and raised
        assert proc.wait_called is True
        # kill should have been called as a fallback
        assert proc.killed is True

        # server_process cleared
        assert rt.server_process is None

        # rmtree called and temp workspace cleared
        assert called.get("path") == "/tmp/fake-timeout-081"
        assert rt._temp_workspace is None

        # parent close called
        assert getattr(rt, "_super_closed", False) is True
    finally:
        local_runtime.shutil.rmtree = shutil_rmtree_orig
        local_runtime.ActionExecutionClient.close = parent_close_orig
        if running_orig is None:
            delattr(local_runtime, "_RUNNING_SERVERS")
        else:
            local_runtime._RUNNING_SERVERS = running_orig
