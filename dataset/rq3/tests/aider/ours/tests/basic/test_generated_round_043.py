import pytest
from io import BytesIO
import aider.run_cmd as run_cmd_module
from aider.run_cmd import run_cmd_pexpect


class _FakeChildSuccess:
    def __init__(self, data=b""):
        # allow setting what to send to output_filter
        self._data = data
        self.exitstatus = 0
        self.closed = False

    def interact(self, output_filter=None):
        # emulate pexpect behavior by calling the output_filter with bytes
        if output_filter is not None:
            # deliver the preconfigured bytes to the callback
            output_filter(self._data)

    def close(self):
        self.closed = True


class _FakeChildStrOutput:
    def __init__(self, data="string-output"):
        # will send a str to the output_filter to provoke a TypeError when
        # the real output_callback (which writes bytes) is invoked
        self._data = data
        self.exitstatus = 0

    def interact(self, output_filter=None):
        if output_filter is not None:
            # intentionally pass a str to provoke TypeError in output_callback
            output_filter(self._data)

    def close(self):
        pass


def test_shell_exists_success_round_043(monkeypatch, capsys):
    """
    - Simulate that the SHELL exists and pexpect.spawn works normally.
    - Ensure verbose prints are produced and successful output is returned.
    """
    # Ensure the module will pick up a shell path from the environment
    monkeypatch.setenv("SHELL", "/bin/fake-shell")

    # Make os.path.exists(path) return True (shell exists)
    monkeypatch.setattr('aider.run_cmd.os.path.exists', lambda path: True)

    # Provide a fake spawn that returns a child which writes bytes to the output
    def fake_spawn(*args, **kwargs):
        # return a child that will send bytes b'hello' to the output_callback
        return _FakeChildSuccess(data=b"hello")

    monkeypatch.setattr('aider.run_cmd.pexpect.spawn', fake_spawn)

    status, out = run_cmd_pexpect("echo hi", verbose=True, cwd="/tmp")

    # validate returned values and printed verbose lines
    captured = capsys.readouterr()
    assert status == 0 and out == "hello"
    # verbose true should have printed the entry trace lines
    assert "Using run_cmd_pexpect:" in captured.out
    assert "With shell:" in captured.out
    assert "Running pexpect.spawn with shell:" in captured.out


def test_no_shell_error_round_043(monkeypatch):
    """
    - Simulate the SHELL does not exist so the code falls back to spawning the
      command directly. The fake child sends a str to output_filter which will
      cause the BytesIO.write to raise TypeError inside the output_callback.
    - The function should catch the TypeError and return (1, error_msg).
    """
    monkeypatch.setenv("SHELL", "/nonexistent")

    # Emulate that the configured shell path does not exist
    monkeypatch.setattr('aider.run_cmd.os.path.exists', lambda path: False)

    def fake_spawn_no_shell(*args, **kwargs):
        # spawn called with the command directly; return a child that will
        # pass a str into the output callback to trigger a TypeError
        return _FakeChildStrOutput(data="not-bytes")

    monkeypatch.setattr('aider.run_cmd.pexpect.spawn', fake_spawn_no_shell)

    status, msg = run_cmd_pexpect("echo error", verbose=True, cwd=None)

    # Should have caught the TypeError and returned exit status 1
    assert status == 1
    assert msg.startswith("Error running command echo error:")
    # message should mention the type of error (bytes-like requirement)
    assert "bytes" in msg or "bytes-like" in msg


def test_verbose_false_round_043(monkeypatch, capsys):
    """
    - Ensure that when verbose=False no verbose prints are produced, but
      the underlying spawn/interact still returns output correctly.
    """
    monkeypatch.setenv("SHELL", "/bin/fake-shell")
    monkeypatch.setattr('aider.run_cmd.os.path.exists', lambda path: True)

    def fake_spawn_quiet(*args, **kwargs):
        return _FakeChildSuccess(data=b"quiet-output")

    monkeypatch.setattr('aider.run_cmd.pexpect.spawn', fake_spawn_quiet)

    status, out = run_cmd_pexpect("some-cmd", verbose=False, cwd=None)

    captured = capsys.readouterr()
    # verbose False: nothing printed to stdout
    assert captured.out == ""
    assert status == 0
    assert out == "quiet-output"
