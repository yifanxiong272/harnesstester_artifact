import types
from unittest.mock import Mock
import aider.io as io_mod


class _Result:
    def __init__(self, returncode=0, stderr=b""):
        self.returncode = returncode
        self.stderr = stderr


def _make_self(bell=True, notifications=True, notifications_command=None, warn_list=None):
    """Create a lightweight self-like object with the attributes used by ring_bell.
    Provide a tool_warning method that appends messages to warn_list (if given).
    """
    obj = types.SimpleNamespace()
    obj.bell_on_next_input = bell
    obj.notifications = notifications
    obj.notifications_command = notifications_command

    recorded = [] if warn_list is None else warn_list

    def tool_warning(msg):
        recorded.append(msg)

    # Attach method required by ring_bell
    obj.tool_warning = tool_warning
    # expose recorded list for assertions
    obj._recorded_warnings = recorded
    return obj


def test_ring_bell_success_round_121(monkeypatch):
    """When subprocess.run returns returncode 0, no tool_warning is called and bell flag is cleared."""
    self_obj = _make_self(bell=True, notifications=True, notifications_command="cmd")

    # Patch subprocess.run used in the module to return a success result
    monkeypatch.setattr(io_mod, "subprocess", Mock(run=Mock(return_value=_Result(returncode=0, stderr=b""))))

    # Call the actual class method function with our fake self
    io_mod.InputOutput.ring_bell(self_obj)

    # No warning should have been recorded
    assert self_obj._recorded_warnings == []
    # Flag should be cleared regardless
    assert self_obj.bell_on_next_input is False


def test_ring_bell_nonzero_stderr_round_121(monkeypatch):
    """When subprocess.run returns non-zero and has stderr, tool_warning is invoked with decoded message."""
    self_obj = _make_self(bell=True, notifications=True, notifications_command="cmd")

    monkeypatch.setattr(io_mod, "subprocess", Mock(run=Mock(return_value=_Result(returncode=2, stderr=b"some error bytes"))))

    io_mod.InputOutput.ring_bell(self_obj)

    # Expect a single warning message containing the decoded stderr
    assert len(self_obj._recorded_warnings) == 1
    assert "Failed to run notifications command:" in self_obj._recorded_warnings[0]
    assert "some error bytes" in self_obj._recorded_warnings[0]
    assert self_obj.bell_on_next_input is False


def test_ring_bell_exception_round_121(monkeypatch):
    """If subprocess.run raises, the exception is caught and tool_warning is called with exception text."""
    self_obj = _make_self(bell=True, notifications=True, notifications_command="cmd")

    def _raiser(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(io_mod, "subprocess", Mock(run=Mock(side_effect=_raiser)))

    io_mod.InputOutput.ring_bell(self_obj)

    assert len(self_obj._recorded_warnings) == 1
    # The message should contain exception stringified
    assert "Failed to run notifications command:" in self_obj._recorded_warnings[0]
    assert "boom" in self_obj._recorded_warnings[0]
    assert self_obj.bell_on_next_input is False


def test_ring_bell_prints_bell_when_no_command_round_121(capsys):
    """When notifications_command is not set, ring_bell should print the audible bell char and clear the flag."""
    self_obj = _make_self(bell=True, notifications=True, notifications_command=None)

    # Ensure subprocess.run is not accidentally called; patch it to raise if used
    # Bind a dummy module object with run that would raise to detect misuse
    dummy = Mock()
    dummy.run = Mock(side_effect=AssertionError("subprocess.run should not be called when notifications_command is falsy"))

    # Patch the module-level subprocess to our dummy to ensure determinism
    # (if rung, it will fail the test)
    from unittest import mock

    with mock.patch.object(io_mod, "subprocess", dummy):
        io_mod.InputOutput.ring_bell(self_obj)

    captured = capsys.readouterr()
    # The code prints the bell character without newline
    assert captured.out == "\a"
    assert captured.err == ""
    assert self_obj._recorded_warnings == []
    assert self_obj.bell_on_next_input is False
