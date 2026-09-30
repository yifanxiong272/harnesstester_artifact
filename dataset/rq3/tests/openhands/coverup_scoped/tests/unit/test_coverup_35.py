# file: openhands/runtime/impl/local/local_runtime.py:775-828
# asked: {"lines": [780, 781, 782, 783, 784, 788, 791, 792, 793, 794, 795, 798, 799, 800, 802, 803, 804, 805, 806, 807, 808, 810, 811, 814, 815, 816, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828], "branches": [[799, 800], [799, 802], [818, 0], [818, 819], [820, 821], [820, 826], [827, 0], [827, 828]]}
# gained: {"lines": [780, 781, 782, 783, 784, 788, 815, 816, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828], "branches": [[818, 819], [820, 821], [827, 828]]}

import os
import shutil
import subprocess
import threading
from types import SimpleNamespace

import pytest

import openhands.runtime.impl.local.local_runtime as local_runtime


class ProcessSpy:
    def __init__(self, wait_raises=False):
        self.terminate_called = False
        self.wait_called = False
        self.kill_called = False
        self._wait_raises = wait_raises

    def terminate(self):
        self.terminate_called = True

    def wait(self, timeout=None):
        self.wait_called = True
        if self._wait_raises:
            # raise the same exception type the real code expects
            raise subprocess.TimeoutExpired(cmd="proc", timeout=timeout)
        return 0

    def kill(self):
        self.kill_called = True

    def poll(self):
        # not used in these tests (session creation fails before poll would be checked),
        # but provide a default implementation
        return None


class LogThreadSpy:
    def __init__(self):
        self.join_called = False

    def join(self, timeout=None):
        self.join_called = True


class ExitEventSpy:
    def __init__(self):
        self.set_called = False

    def set(self):
        self.set_called = True


def make_server_info(tmp_path, wait_raises=False):
    proc = ProcessSpy(wait_raises=wait_raises)
    log_thread = LogThreadSpy()
    log_event = ExitEventSpy()
    temp_workspace = str(tmp_path / "temp_ws")
    os.makedirs(temp_workspace, exist_ok=True)
    info = SimpleNamespace(
        process=proc,
        log_thread=log_thread,
        log_thread_exit_event=log_event,
        execution_server_port=12345,
        temp_workspace=temp_workspace,
    )
    return info


def raising_httpx_client(*args, **kwargs):
    # Simulate that instantiating the HTTP client fails immediately
    raise RuntimeError("httpx client creation failed")


def test_create_warm_server_cleanup_kill_on_timeout(monkeypatch, tmp_path):
    """
    Test that when an exception occurs after server_info is created, the cleanup path
    is executed and handles subprocess.TimeoutExpired by calling kill().
    """
    # Prepare a server_info whose process.wait will raise TimeoutExpired
    server_info = make_server_info(tmp_path, wait_raises=True)
    api_url = "http://127.0.0.1:5678"

    # Monkeypatch _create_server to return our server_info and api_url
    def fake_create_server(config, plugins, workspace_prefix):
        return server_info, api_url

    monkeypatch.setattr(local_runtime, "_create_server", fake_create_server)

    # Monkeypatch httpx.Client in the module to raise on instantiation so the exception
    # is thrown before wait_until_alive is invoked (avoids tenacity retries).
    monkeypatch.setattr(local_runtime.httpx, "Client", raising_httpx_client)

    # Spy on logger.error to confirm it's called
    error_called = {"called": False, "msg": None}

    def fake_logger_error(msg):
        error_called["called"] = True
        error_called["msg"] = msg

    monkeypatch.setattr(local_runtime.logger, "error", fake_logger_error)

    # Run the function (should not raise)
    local_runtime._create_warm_server(config=None, plugins=[])

    # Assertions: ensure cleanup path ran
    assert error_called["called"], "logger.error was not called during cleanup"
    assert "Failed to create warm server" in error_called["msg"]

    # process termination/wait/kill should have been invoked
    assert server_info.process.terminate_called, "process.terminate was not called"
    assert server_info.process.wait_called, "process.wait was not called"
    assert server_info.process.kill_called, "process.kill was not called (expected due to TimeoutExpired)"

    # log thread join should have been called
    assert server_info.log_thread.join_called, "log_thread.join was not called"

    # log thread exit event should have been set
    assert server_info.log_thread_exit_event.set_called, "log_thread_exit_event.set was not called"

    # temp workspace should have been removed
    assert not os.path.exists(server_info.temp_workspace), "temp_workspace was not removed"


def test_create_warm_server_cleanup_no_kill_when_wait_succeeds(monkeypatch, tmp_path):
    """
    Test the cleanup branch where process.wait does not raise TimeoutExpired,
    so kill() should not be called.
    """
    server_info = make_server_info(tmp_path, wait_raises=False)
    api_url = "http://127.0.0.1:9876"

    def fake_create_server(config, plugins, workspace_prefix):
        return server_info, api_url

    monkeypatch.setattr(local_runtime, "_create_server", fake_create_server)
    monkeypatch.setattr(local_runtime.httpx, "Client", raising_httpx_client)

    error_called = {"called": False}

    def fake_logger_error(msg):
        error_called["called"] = True

    monkeypatch.setattr(local_runtime.logger, "error", fake_logger_error)

    # Execute
    local_runtime._create_warm_server(config=None, plugins=[])

    # Ensure cleanup occurred
    assert error_called["called"], "Expected logger.error to be called"
    assert server_info.process.terminate_called, "process.terminate was not called"
    assert server_info.process.wait_called, "process.wait was not called"
    assert not server_info.process.kill_called, "process.kill was called unexpectedly"

    assert server_info.log_thread.join_called, "log_thread.join was not called"
    assert server_info.log_thread_exit_event.set_called, "log_thread_exit_event.set was not called"

    assert not os.path.exists(server_info.temp_workspace), "temp_workspace was not removed"
