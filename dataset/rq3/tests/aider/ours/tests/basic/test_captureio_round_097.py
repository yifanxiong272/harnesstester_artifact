import pytest


def _reset_captureio_lines(module):
    # Ensure class attribute is in a known state before each test
    module.CaptureIO.lines = []


def test_tool_output_appends_and_calls_super_round_097(monkeypatch):
    """When log_only is False, message should be appended and super.tool_output called."""
    from aider import gui
    from aider import io as aio

    _reset_captureio_lines(gui)

    super_calls = []

    def fake_tool_output(self, msg, log_only=False):
        # record the call so we can assert it happened
        super_calls.append((msg, log_only))

    # Patch the method on the InputOutput class that CaptureIO will call via super()
    monkeypatch.setattr(aio.InputOutput, "tool_output", fake_tool_output, raising=True)

    inst = gui.CaptureIO()
    inst.tool_output("hello-world", log_only=False)

    # The CaptureIO implementation should append the message when log_only is False
    assert gui.CaptureIO.lines == ["hello-world"]

    # And the patched super() method should have been invoked with the same args
    assert super_calls == [("hello-world", False)]


def test_tool_output_log_only_true_calls_super_no_append_round_097(monkeypatch):
    """When log_only is True, message must NOT be appended but super.tool_output is still called."""
    from aider import gui
    from aider import io as aio

    # Start with a sentinel existing list to ensure no append occurs
    gui.CaptureIO.lines = ["existing"]

    super_calls = []

    def fake_tool_output(self, msg, log_only=False):
        super_calls.append((msg, log_only))

    monkeypatch.setattr(aio.InputOutput, "tool_output", fake_tool_output, raising=True)

    inst = gui.CaptureIO()
    inst.tool_output("should_not_append", log_only=True)

    # The class-level list should remain unchanged because log_only True prevents append
    assert gui.CaptureIO.lines == ["existing"]

    # The super method should still be called with the provided args
    assert super_calls == [("should_not_append", True)]


def test_error_warning_and_get_captured_lines_round_097(monkeypatch):
    """tool_error and tool_warning append messages; get_captured_lines returns captured list and
    subsequent calls reflect reset instance-level storage."""
    from aider import gui
    from aider import io as aio

    _reset_captureio_lines(gui)

    calls = []

    def fake_error(self, msg):
        calls.append(("error", msg))

    def fake_warning(self, msg):
        calls.append(("warning", msg))

    monkeypatch.setattr(aio.InputOutput, "tool_error", fake_error, raising=True)
    monkeypatch.setattr(aio.InputOutput, "tool_warning", fake_warning, raising=True)

    inst = gui.CaptureIO()

    # Call error and warning; both should append to the capture list
    inst.tool_error("err-1")
    inst.tool_warning("warn-1")

    # Because CaptureIO starts with a shared class-list, these entries will be visible there
    assert gui.CaptureIO.lines == ["err-1", "warn-1"]

    # The patched super methods should have been invoked
    assert ("error", "err-1") in calls
    assert ("warning", "warn-1") in calls

    # get_captured_lines should return the captured list (the messages appended above)
    captured = inst.get_captured_lines()
    assert captured == ["err-1", "warn-1"]

    # After the call, the instance's .lines should have been set to a fresh empty list
    assert getattr(inst, "lines") == []

    # Subsequent call on the same instance returns an empty list (the instance-level storage)
    assert inst.get_captured_lines() == []
