import signal
from types import SimpleNamespace

import pytest

from openhands.runtime.impl.cli.cli_runtime import (
    CLIRuntime,
    CmdOutputObservation,
)


class _FakeStdout:
    def __init__(self, lines):
        # lines should be an iterable of strings (each including trailing newline if desired)
        self._lines = list(lines)
        self.closed = False

    def readline(self):
        if not self._lines:
            return ''
        return self._lines.pop(0)

    # helper for select simulation
    def has_pending(self):
        return bool(self._lines)


class _FakeProcess:
    def __init__(self, lines, returncode=0, always_poll_none=False):
        self.pid = 4242
        self.stdout = _FakeStdout(lines)
        # store as protected to allow tests to mutate
        self._returncode = returncode
        self._always_poll_none = always_poll_none

    def poll(self):
        if self._always_poll_none:
            return None
        if self.stdout.has_pending():
            return None
        return self._returncode

    @property
    def returncode(self):
        return self._returncode


def _make_dummy_self(workspace_path="/tmp/test_workspace"):
    # Use a SimpleNamespace as the 'self' object passed to the bound function.
    s = SimpleNamespace()
    s._workspace_path = workspace_path
    s._shell_stream_callback = None

    # record termination calls
    s._terminate_calls = []

    def _safe_terminate_process(process, signal_to_send=None):
        s._terminate_calls.append((process, signal_to_send))
        try:
            process._returncode = -1
        except Exception:
            pass

    s._safe_terminate_process = _safe_terminate_process
    return s


def test_execute_shell_command_reads_lines_and_streams_callback_round_008(monkeypatch):
    """Simulate a process that outputs two lines and exits normally.

    Assertions:
    - Callback is called with each line
    - CmdOutputObservation contains the concatenated content
    - exit_code equals the fake process returncode
    - metadata.working_dir equals the workspace path and no timeout suffix
    """
    fake_lines = ["first line\n", "second line\n"]
    fake_proc = _FakeProcess(lines=fake_lines.copy(), returncode=0)

    # Patch subprocess.Popen to return our fake process
    monkeypatch.setattr(
        "openhands.runtime.impl.cli.cli_runtime.subprocess.Popen",
        lambda *args, **kwargs: fake_proc,
    )

    # Patch select.select so readable only when fake stdout has pending content
    def fake_select(read_list, write_list, exc_list, timeout=None):
        if read_list and getattr(read_list[0], "has_pending", lambda: False)():
            return ([read_list[0]], [], [])
        return ([], [], [])

    monkeypatch.setattr(
        "openhands.runtime.impl.cli.cli_runtime.select.select",
        fake_select,
    )

    # Prepare dummy self and a callback to capture streamed lines
    dummy = _make_dummy_self()
    seen = []

    def cb(line):
        seen.append(line)

    dummy._shell_stream_callback = cb

    # Call the function under test
    obs = CLIRuntime._execute_shell_command(dummy, "echo simulated", timeout=None)

    assert isinstance(obs, CmdOutputObservation)
    # content should be the two lines in order
    assert obs.content == "first line\nsecond line\n"
    assert obs.exit_code == 0
    # metadata is a Pydantic model; access attributes directly
    assert getattr(obs.metadata, "working_dir") == dummy._workspace_path
    # suffix should be empty string when no timeout happened
    assert getattr(obs.metadata, "suffix") in (None, "", '')
    # callback should have been called for each line seen while streaming
    assert seen == ["first line\n", "second line\n"]


def test_execute_shell_command_timeout_triggers_termination_and_suffix_round_008(monkeypatch):
    """Simulate a process that never becomes ready to read and times out.

    Assertions:
    - _safe_terminate_process is called with SIGTERM
    - the returned observation has exit_code == -1
    - metadata.suffix includes a timeout message
    """
    # Process that will never report readiness and poll always None
    fake_proc = _FakeProcess(lines=[], returncode=None, always_poll_none=True)

    monkeypatch.setattr(
        "openhands.runtime.impl.cli.cli_runtime.subprocess.Popen",
        lambda *args, **kwargs: fake_proc,
    )

    # select.select returns no ready descriptors to force no line reads in the loop
    monkeypatch.setattr(
        "openhands.runtime.impl.cli.cli_runtime.select.select",
        lambda *r, **kw: ([], [], []),
    )

    # Simulate monotonic time advancing so the loop hits the timeout branch.
    times = [0.0, 0.05, 0.2]

    def fake_monotonic():
        if times:
            return times.pop(0)
        return 9999.0

    monkeypatch.setattr(
        "openhands.runtime.impl.cli.cli_runtime.time.monotonic",
        fake_monotonic,
    )

    dummy = _make_dummy_self()

    obs = CLIRuntime._execute_shell_command(dummy, "sleep_forever", timeout=0.1)

    # The instance's _safe_terminate_process should have been invoked with SIGTERM
    assert dummy._terminate_calls, "_safe_terminate_process was not called"
    proc_called, sig_called = dummy._terminate_calls[0]
    assert proc_called is fake_proc
    assert sig_called == signal.SIGTERM

    # After timeout, the function ensures exit_code == -1 and sets suffix metadata
    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == -1
    assert getattr(obs.metadata, "working_dir") == dummy._workspace_path
    suffix_val = getattr(obs.metadata, "suffix") or ""
    assert "timed out" in suffix_val
