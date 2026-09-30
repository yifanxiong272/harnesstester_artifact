import signal
import subprocess
import select
import time
import pytest

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime, CmdOutputObservation


def test_execute_shell_capture_output_round_008(monkeypatch):
    """Normal run: subprocess yields two lines and exits normally.

    This test patches subprocess.Popen, select.select and time.monotonic to
    deterministic fakes. It verifies content, exit_code and that the
    _shell_stream_callback is called for each streamed line.
    """
    # Prepare a dummy CLIRuntime instance without running __init__
    inst = CLIRuntime.__new__(CLIRuntime)
    inst._workspace_path = "/fake/workdir"

    seen_callbacks = []

    def stream_cb(line):
        seen_callbacks.append(line)

    inst._shell_stream_callback = stream_cb

    safe_calls = []

    def fake_safe_terminate(process, signal_to_send):
        # record termination attempts
        safe_calls.append((process, signal_to_send))
        # simulate process ending after termination
        process.returncode = 0

    inst._safe_terminate_process = fake_safe_terminate

    # Fake stdout that returns two lines then EOF
    class FakeStdout:
        def __init__(self, lines):
            self._lines = list(lines)
            self.closed = False

        def readline(self):
            return self._lines.pop(0) if self._lines else ""

    # Fake process with predictable poll behavior
    class FakeProcess:
        def __init__(self, lines):
            self.pid = 12345
            self.stdout = FakeStdout(lines)
            self.returncode = 0
            self._poll_calls = 0

        def poll(self):
            # Return None the first time to enter the loop, then 0 to finish
            self._poll_calls += 1
            return None if self._poll_calls < 2 else 0

    fake_proc = FakeProcess(["first\n", "second\n"])

    # Patch subprocess.Popen to return our fake process
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: fake_proc)

    # Patch select.select to indicate stdout ready while there are lines
    def fake_select(r, w, x, timeout):
        return ([fake_proc.stdout], [], []) if fake_proc.stdout._lines else ([], [], [])

    monkeypatch.setattr(select, "select", fake_select)

    # Patch time.monotonic to a fixed value so timeout logic does not trigger
    monkeypatch.setattr(time, "monotonic", lambda: 0.0)

    obs = inst._execute_shell_command("echo 'hi'", timeout=1.0)

    assert isinstance(obs, CmdOutputObservation)
    assert obs.command == "echo 'hi'"
    # Both lines should be present in the content
    assert "first\n" in obs.content and "second\n" in obs.content
    # process.returncode was 0 and no timeout happened
    assert obs.exit_code == 0
    # callback should have been invoked for each streamed line
    assert seen_callbacks == ["first\n", "second\n"]
    # No timeout suffix expected
    # metadata is a pydantic model object; check attribute
    assert getattr(obs, "metadata") is not None
    assert not getattr(obs.metadata, "suffix", None)


def test_execute_shell_timeout_and_read_exception_round_008(monkeypatch):
    """Timeout path: no streaming reads happen, monotonic advances past timeout.

    This triggers the timed_out branch and causes the 'remaining read'
    block to hit an exception (because 'line' is never defined), exercising
    the except path and ensuring _safe_terminate_process is called with SIGTERM.
    """
    inst = CLIRuntime.__new__(CLIRuntime)
    inst._workspace_path = "/fake/workdir"
    inst._shell_stream_callback = None

    safe_calls = []

    def fake_safe_terminate(process, signal_to_send):
        safe_calls.append(signal_to_send)
        # simulate that the process remains with some returncode; final exit_code is set by timed_out logic
        process.returncode = 42

    inst._safe_terminate_process = fake_safe_terminate

    # Fake stdout whose readline would raise if called
    class ExplodingStdout:
        def __init__(self):
            self.closed = False

        def readline(self):
            raise RuntimeError("read failed")

    class NeverEndingProcess:
        def __init__(self):
            self.pid = 99999
            self.stdout = ExplodingStdout()
            self.returncode = None

        def poll(self):
            # Always indicate still running so loop keeps checking and allows timeout to trigger
            return None

    fake_proc = NeverEndingProcess()

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: fake_proc)

    # select.select never indicates ready_to_read, so 'line' is never defined inside the loop
    monkeypatch.setattr(select, "select", lambda r, w, x, t: ([], [], []))

    # time.monotonic will increase so that we exceed the timeout predictably
    times = {"t": 0.0}

    def advancing_monotonic():
        # each call advances by 0.6 seconds
        times["t"] += 0.6
        return times["t"]

    monkeypatch.setattr(time, "monotonic", advancing_monotonic)

    obs = inst._execute_shell_command("sleep 10", timeout=0.5)

    assert isinstance(obs, CmdOutputObservation)
    # Timeout branch sets exit_code to -1
    assert obs.exit_code == -1
    # Metadata is a pydantic model object; check suffix attribute for message
    suffix_val = getattr(obs.metadata, "suffix", None)
    assert suffix_val is not None and "timed out" in suffix_val
    # _safe_terminate_process should have been called with SIGTERM
    assert safe_calls and safe_calls[0] == signal.SIGTERM
