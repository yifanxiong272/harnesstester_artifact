# file: openhands/runtime/impl/local/local_runtime.py:652-772
# asked: {"lines": [657, 660, 661, 663, 666, 667, 668, 670, 671, 672, 673, 674, 676, 677, 678, 679, 684, 687, 688, 689, 690, 691, 693, 694, 697, 699, 701, 702, 703, 704, 705, 708, 710, 712, 713, 716, 717, 718, 719, 722, 725, 726, 727, 728, 730, 732, 733, 734, 735, 736, 737, 738, 739, 742, 743, 744, 745, 746, 747, 749, 750, 752, 754, 755, 758, 759, 760, 761, 762, 763, 764, 765, 766, 770, 772], "branches": [[726, 727], [726, 730], [732, 733], [732, 742], [733, 734], [733, 736], [737, 738], [737, 739], [742, 743], [742, 752], [744, 745], [744, 752], [745, 746], [745, 747]]}
# gained: {"lines": [657, 660, 661, 663, 666, 667, 668, 670, 671, 672, 673, 674, 676, 677, 678, 679, 684, 687, 688, 689, 690, 691, 693, 694, 697, 699, 701, 702, 703, 704, 705, 708, 710, 712, 713, 716, 717, 718, 719, 722, 725, 726, 730, 732, 733, 736, 737, 738, 739, 742, 743, 744, 745, 747, 752, 754, 755, 758, 759, 760, 761, 762, 763, 764, 765, 766, 770, 772], "branches": [[726, 730], [732, 733], [732, 742], [733, 736], [737, 738], [737, 739], [742, 743], [744, 745], [744, 752], [745, 747]]}

import os
import threading
from types import SimpleNamespace

import pytest

import openhands.runtime.impl.local.local_runtime as local_runtime


class FakeStdout:
    def __init__(self, initial_lines=None, remaining_lines=None):
        self._initial = list(initial_lines or [])
        self._remaining = list(remaining_lines or [])
        # Make iterator stateful for "for line in stdout:" usage
        self._iter_index = 0

    def readline(self):
        if self._initial:
            return self._initial.pop(0)
        return ""

    def __iter__(self):
        # Return an iterator over remaining lines
        return iter(self._remaining)


class FakeProcess:
    def __init__(self, stdout: FakeStdout, poll_sequence=None):
        self.stdout = stdout
        self._poll_sequence = list(poll_sequence or [None, 0])
        self._poll_calls = 0

    def poll(self):
        # Return subsequent values from sequence, last value repeats
        if self._poll_calls < len(self._poll_sequence):
            val = self._poll_sequence[self._poll_calls]
        else:
            val = self._poll_sequence[-1]
        self._poll_calls += 1
        return val


def make_config(local_runtime_url: str):
    # Minimal object with attribute used by the function
    sandbox = SimpleNamespace(local_runtime_url=local_runtime_url)
    return SimpleNamespace(sandbox=sandbox)


def test_create_server_with_env_ports(monkeypatch, tmp_path):
    # Prepare temp workspace directory returned by tempfile.mkdtemp
    workspace_dir = tmp_path / "workspace_env"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(local_runtime.tempfile, "mkdtemp", lambda prefix=None: str(workspace_dir))

    # Ensure openhands.__file__ yields a path two levels down from repo root
    repo_root = tmp_path / "repo_env"
    pkg_dir = repo_root / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    fake_init = pkg_dir / "__init__.py"
    fake_init.write_text("# dummy")
    monkeypatch.setattr(local_runtime.openhands, "__file__", str(fake_init))

    # Mock functions used inside _create_server
    monkeypatch.setattr(local_runtime, "get_user_info", lambda: (12345, "tester"))
    monkeypatch.setattr(local_runtime, "_python_bin_path", lambda: "/fake_python/bin")
    # Command builder
    monkeypatch.setattr(local_runtime, "get_action_execution_server_startup_command", lambda **kw: ["echo", "started"])

    # Force certain find_available_tcp_port return for execution_server_port only
    monkeypatch.setattr(local_runtime, "find_available_tcp_port", lambda a, b: 9000)

    # Set environment variables to take the env branches for ports
    monkeypatch.setenv("VSCODE_PORT", "8001")
    monkeypatch.setenv("WORK_PORT_1", "30001")
    monkeypatch.setenv("WORK_PORT_2", "30002")
    # Also set APP_PORT_* envs to ensure the code prioritizes WORK_PORT over APP_PORT
    monkeypatch.setenv("APP_PORT_1", "40001")
    monkeypatch.setenv("APP_PORT_2", "40002")

    # Setup fake process to be returned by subprocess.Popen
    initial_lines = ["line a\n"]
    remaining_lines = ["remaining 1\n", "remaining 2\n"]
    fake_stdout = FakeStdout(initial_lines=initial_lines, remaining_lines=remaining_lines)
    fake_proc = FakeProcess(stdout=fake_stdout, poll_sequence=[None, 0])

    captured = {}

    def fake_popen(cmd, stdout, stderr, universal_newlines, bufsize, env, cwd):
        # Capture important parameters for assertions
        captured['cmd'] = cmd
        captured['stdout'] = stdout
        captured['stderr'] = stderr
        captured['universal_newlines'] = universal_newlines
        captured['bufsize'] = bufsize
        captured['env'] = env
        captured['cwd'] = cwd
        return fake_proc

    monkeypatch.setattr(local_runtime.subprocess, "Popen", fake_popen)

    # Build config and call function under test
    cfg = make_config("http://localhost")
    server_info, api_url = local_runtime._create_server(cfg, plugins=[], workspace_prefix="envtest")

    # Wait for the logging thread to finish (it should since fake_proc.poll becomes 0)
    server_info.log_thread.join(timeout=2)
    assert not server_info.log_thread.is_alive(), "log thread did not finish as expected"

    # Assertions on returned server_info and api_url
    assert server_info.process is fake_proc
    assert server_info.execution_server_port == 9000
    assert server_info.vscode_port == 8001  # from env
    assert server_info.app_ports == [30001, 30002]  # from WORK_PORT envs
    assert server_info.temp_workspace == str(workspace_dir)
    assert server_info.workspace_mount_path == str(workspace_dir)
    assert api_url == "http://localhost:9000"

    # Ensure Popen was called with cwd equal to repo root (dirname(dirname(openhands.__file__)))
    assert captured['cwd'] == str(repo_root)

    # Clean up environment changes are handled by monkeypatch fixture


def test_create_server_without_env_ports(monkeypatch, tmp_path):
    # No VSCODE_PORT or APP_PORT_* env vars set: test find_available_tcp_port path
    monkeypatch.delenv("VSCODE_PORT", raising=False)
    monkeypatch.delenv("WORK_PORT_1", raising=False)
    monkeypatch.delenv("WORK_PORT_2", raising=False)
    monkeypatch.delenv("APP_PORT_1", raising=False)
    monkeypatch.delenv("APP_PORT_2", raising=False)

    # Prepare temp workspace directory returned by tempfile.mkdtemp
    workspace_dir = tmp_path / "workspace_noenv"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(local_runtime.tempfile, "mkdtemp", lambda prefix=None: str(workspace_dir))

    # Setup openhands.__file__ path two levels deep
    repo_root = tmp_path / "repo_noenv"
    pkg_dir = repo_root / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    fake_init = pkg_dir / "__init__.py"
    fake_init.write_text("# dummy")
    monkeypatch.setattr(local_runtime.openhands, "__file__", str(fake_init))

    # Mock helpers
    monkeypatch.setattr(local_runtime, "get_user_info", lambda: (2222, "nouser"))
    monkeypatch.setattr(local_runtime, "_python_bin_path", lambda: "/another_fake/bin")
    monkeypatch.setattr(local_runtime, "get_action_execution_server_startup_command", lambda **kw: ["python", "-m", "openhands.server"])

    # Create a generator for sequential ports: execution, vscode, app1, app2
    ports = iter([9100, 9101, 9102, 9103])

    def fake_find_available_tcp_port(a, b):
        return next(ports)

    monkeypatch.setattr(local_runtime, "find_available_tcp_port", fake_find_available_tcp_port)

    # Fake process: produce no initial lines but some remaining lines, and poll sequence to exit after first check
    fake_stdout = FakeStdout(initial_lines=[], remaining_lines=["r1\n"])
    fake_proc = FakeProcess(stdout=fake_stdout, poll_sequence=[None, 0])

    captured = {}

    def fake_popen(cmd, stdout, stderr, universal_newlines, bufsize, env, cwd):
        captured['cmd'] = cmd
        captured['env'] = env
        captured['cwd'] = cwd
        return fake_proc

    monkeypatch.setattr(local_runtime.subprocess, "Popen", fake_popen)

    cfg = make_config("http://0.0.0.0")
    server_info, api_url = local_runtime._create_server(cfg, plugins=[], workspace_prefix="noenvtest")

    # Wait for log thread to finish
    server_info.log_thread.join(timeout=2)
    assert not server_info.log_thread.is_alive()

    # Assert ports came from our generator
    assert server_info.execution_server_port == 9100
    assert server_info.vscode_port == 9101
    assert server_info.app_ports == [9102, 9103]
    assert api_url == "http://0.0.0.0:9100"

    # Ensure PYTHONPATH and OPENHANDS_REPO_PATH were set in env passed to Popen
    env_passed = captured['env']
    assert 'PYTHONPATH' in env_passed and env_passed['OPENHANDS_REPO_PATH'] == str(repo_root)
    # PATH should have our fake python bin path at the start
    assert env_passed['PATH'].startswith("/another_fake/bin")
    assert captured['cwd'] == str(repo_root)
