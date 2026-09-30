# file: openhands/runtime/impl/local/local_runtime.py:652-772
# asked: {"lines": [657, 660, 661, 663, 666, 667, 668, 670, 671, 672, 673, 674, 676, 677, 678, 679, 684, 687, 688, 689, 690, 691, 693, 694, 697, 699, 701, 702, 703, 704, 705, 708, 710, 712, 713, 716, 717, 718, 719, 722, 725, 726, 727, 728, 730, 732, 733, 734, 735, 736, 737, 738, 739, 742, 743, 744, 745, 746, 747, 749, 750, 752, 754, 755, 758, 759, 760, 761, 762, 763, 764, 765, 766, 770, 772], "branches": [[726, 727], [726, 730], [732, 733], [732, 742], [733, 734], [733, 736], [737, 738], [737, 739], [742, 743], [742, 752], [744, 745], [744, 752], [745, 746], [745, 747]]}
# gained: {"lines": [657, 660, 661, 663, 666, 667, 668, 670, 671, 672, 673, 674, 676, 677, 678, 679, 684, 687, 688, 689, 690, 691, 693, 694, 697, 699, 701, 702, 703, 704, 705, 708, 710, 712, 713, 716, 717, 718, 719, 722, 725, 726, 727, 728, 730, 732, 742, 743, 744, 745, 747, 752, 754, 755, 758, 759, 760, 761, 762, 763, 764, 765, 766, 770, 772], "branches": [[726, 727], [726, 730], [732, 742], [742, 743], [744, 745], [744, 752], [745, 747]]}

import io
import os
import shutil
import threading

import pytest

from openhands.runtime.impl.local import local_runtime as local_runtime_module


class DummySandbox:
    def __init__(self, local_runtime_url: str):
        self.local_runtime_url = local_runtime_url


class DummyConfig:
    def __init__(self, local_runtime_url: str = "http://127.0.0.1"):
        self.sandbox = DummySandbox(local_runtime_url)


class FakeProcWithOutput:
    def __init__(self, text: str, poll_returns=1):
        # StringIO supports readline and iteration
        self.stdout = io.StringIO(text)
        self._poll_returns = poll_returns
        self._terminated = False
        self.returncode = poll_returns

    def poll(self):
        return self._poll_returns

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._terminated = True


class FakeProcNoStdout:
    def __init__(self, poll_returns=None):
        self.stdout = None
        self._poll_returns = poll_returns

    def poll(self):
        return self._poll_returns

    def terminate(self):
        pass

    def kill(self):
        pass


def _wait_for_thread_finish(thread: threading.Thread, timeout: float = 2.0):
    thread.join(timeout=timeout)
    # After join, thread should not be alive (or at least join returned).
    assert not thread.is_alive()


def test_create_server_reads_remaining_output_and_returns_api_url(monkeypatch, tmp_path):
    # Prepare sequence of ports: execution_server_port, vscode_port, app_port1, app_port2
    ports = [8000, 9000, 10000, 10001]

    def fake_find_available_tcp_port(start, end):
        return ports.pop(0)

    monkeypatch.setattr(local_runtime_module, "find_available_tcp_port", fake_find_available_tcp_port)

    # Ensure no interfering env vars
    monkeypatch.delenv("VSCODE_PORT", raising=False)
    monkeypatch.delenv("WORK_PORT_1", raising=False)
    monkeypatch.delenv("APP_PORT_1", raising=False)
    monkeypatch.delenv("WORK_PORT_2", raising=False)
    monkeypatch.delenv("APP_PORT_2", raising=False)

    # Patch get_user_info
    monkeypatch.setattr(local_runtime_module, "get_user_info", lambda: (1234, "testuser"))

    # Patch startup command generator to return a benign command list
    monkeypatch.setattr(local_runtime_module, "get_action_execution_server_startup_command", lambda **kwargs: ["echo", "started"])

    # Patch _python_bin_path
    monkeypatch.setattr(local_runtime_module, "_python_bin_path", lambda: "/fake/python/bin")

    # Fake subprocess.Popen to return a process whose poll() != None immediately and has stdout with lines
    fake_proc = FakeProcWithOutput("first line\nsecond line\n")
    def fake_popen(cmd, stdout, stderr, universal_newlines, bufsize, env, cwd):
        # verify some expected environment values are present
        assert "LOCAL_RUNTIME_MODE" in env and env["LOCAL_RUNTIME_MODE"] == "1"
        # Return our fake process
        return fake_proc

    monkeypatch.setattr(local_runtime_module.subprocess, "Popen", fake_popen)

    cfg = DummyConfig(local_runtime_url="http://localhost")
    server_info, api_url = local_runtime_module._create_server(cfg, plugins=[], workspace_prefix="unittest")

    # api_url should include execution server port we returned first
    assert api_url.endswith(":8000")

    # Verify server_info fields
    assert server_info.execution_server_port == 8000
    assert server_info.vscode_port == 9000
    assert server_info.app_ports == [10000, 10001]
    assert os.path.isdir(server_info.temp_workspace)
    assert server_info.workspace_mount_path == server_info.temp_workspace
    # process should be our fake_proc
    assert server_info.process is fake_proc

    # Wait for log thread to finish
    _wait_for_thread_finish(server_info.log_thread)

    # Cleanup temporary workspace
    shutil.rmtree(server_info.temp_workspace, ignore_errors=True)


def test_create_server_handles_no_stdout_early_return(monkeypatch):
    # Prepare sequence of ports: execution_server_port, vscode_port, app_port1, app_port2
    ports = [8001, 9001, 10002, 10003]

    def fake_find_available_tcp_port(start, end):
        return ports.pop(0)

    monkeypatch.setattr(local_runtime_module, "find_available_tcp_port", fake_find_available_tcp_port)

    # Ensure no interfering env vars
    monkeypatch.delenv("VSCODE_PORT", raising=False)
    monkeypatch.delenv("WORK_PORT_1", raising=False)
    monkeypatch.delenv("APP_PORT_1", raising=False)
    monkeypatch.delenv("WORK_PORT_2", raising=False)
    monkeypatch.delenv("APP_PORT_2", raising=False)

    # Patch get_user_info
    monkeypatch.setattr(local_runtime_module, "get_user_info", lambda: (4321, "nouserout"))

    # Patch startup command generator and python bin path
    monkeypatch.setattr(local_runtime_module, "get_action_execution_server_startup_command", lambda **kwargs: ["echo", "no-stdout"])
    monkeypatch.setattr(local_runtime_module, "_python_bin_path", lambda: "/fake/python/bin2")

    # Fake subprocess.Popen to return a process with stdout = None
    fake_proc = FakeProcNoStdout(poll_returns=None)
    def fake_popen(cmd, stdout, stderr, universal_newlines, bufsize, env, cwd):
        return fake_proc

    monkeypatch.setattr(local_runtime_module.subprocess, "Popen", fake_popen)

    cfg = DummyConfig(local_runtime_url="http://127.0.0.1")
    server_info, api_url = local_runtime_module._create_server(cfg, plugins=[], workspace_prefix="unittest_no_stdout")

    # api_url should include execution server port we returned first
    assert api_url.endswith(":8001")

    # Ensure process stdout is None as we simulated
    assert server_info.process.stdout is None

    # Wait for log thread to finish
    _wait_for_thread_finish(server_info.log_thread)

    # Cleanup temporary workspace
    shutil.rmtree(server_info.temp_workspace, ignore_errors=True)
