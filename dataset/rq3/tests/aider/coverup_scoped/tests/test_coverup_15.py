# file: aider/waiting.py:105-160
# asked: {"lines": [112, 113, 114, 115, 116, 117, 119, 120, 122, 123, 127, 128, 129, 131, 132, 135, 136, 138, 141, 144, 145, 148, 151, 158, 159, 160], "branches": [[109, 112], [113, 114], [113, 119], [116, 117], [116, 119], [119, 120], [119, 122], [128, 129], [128, 131], [135, 136], [135, 138]]}
# gained: {"lines": [112, 113, 114, 115, 116, 117, 119, 122, 123, 127, 128, 129, 131, 132, 135, 136, 138, 141, 144, 145, 148, 151, 158, 159, 160], "branches": [[109, 112], [113, 114], [116, 117], [119, 122], [128, 129], [128, 131], [135, 136], [135, 138]]}

import types

import pytest

import aider.waiting as waiting_module


class FakeStdOut:
    def __init__(self, isatty_value=True):
        self._writes = []
        self._flush_called = False
        self._isatty = isatty_value

    def isatty(self):
        return self._isatty

    def write(self, s):
        # store actual strings written for assertions
        self._writes.append(s)
        # mimic real stdout.write by returning number of chars written
        return len(s)

    def flush(self):
        self._flush_called = True

    @property
    def writes(self):
        return self._writes

    @property
    def flush_called(self):
        return self._flush_called


class FakeConsole:
    def __init__(self, width):
        self.width = width
        self.show_cursor_calls = []

    def show_cursor(self, flag: bool):
        self.show_cursor_calls.append(flag)


def test_step_handles_extremely_narrow_terminal(monkeypatch):
    """
    Exercise branch where console.width - 2 < 0 leading to max_spinner_width = 0,
    and where the scan character position is beyond total_chars_written_on_line
    so that no backspaces are actually written.
    """
    fake_out = FakeStdOut(isatty_value=True)
    # Patch the stdout used by the module so Spinner.__init__ and _supports_unicode write to fake_out
    monkeypatch.setattr(waiting_module, "sys", types.SimpleNamespace(stdout=fake_out))
    # Make time.time return a stable value
    monkeypatch.setattr(waiting_module.time, "time", lambda: 100.0)

    spinner = waiting_module.Spinner("txt")
    # Clear any writes that occurred during __init__ (from _supports_unicode)
    fake_out._writes.clear()
    fake_out._flush_called = False

    # Replace console with a fake console with width small enough to make max_spinner_width < 0
    spinner.console = FakeConsole(width=1)  # max_spinner_width = -1 -> coerced to 0
    # Ensure spinner appears eligible to become visible
    spinner.start_time = 99.0  # now - start_time = 1.0 >= 0.5

    # Pre-conditions
    assert spinner.is_tty is True
    assert spinner.visible is False

    # Call step: should set visible True, call console.show_cursor(False), and write only '\r' (empty line)
    spinner.step()

    # Post-conditions
    assert spinner.visible is True
    # console.show_cursor was called with False
    assert spinner.console.show_cursor_calls == [False]
    # last_display_len should be zero due to truncation to max_spinner_width 0
    assert spinner.last_display_len == 0

    # Check writes: first write should be '\r' (since line_to_display empty)
    assert len(fake_out.writes) >= 2
    first_write = fake_out.writes[0]
    second_write = fake_out.writes[1]
    assert first_write == "\r"
    # second_write should be empty string because num_backspaces was negative -> zero backspaces
    assert second_write == ""
    assert fake_out.flush_called is True


def test_step_writes_backspaces_and_updates_last_display_len(monkeypatch):
    """
    Exercise normal path where the spinner writes a frame plus text, computes padding,
    writes backspaces (positive count), and updates last_display_len and flush.
    """
    fake_out = FakeStdOut(isatty_value=True)
    monkeypatch.setattr(waiting_module, "sys", types.SimpleNamespace(stdout=fake_out))
    # Start at a stable time
    monkeypatch.setattr(waiting_module.time, "time", lambda: 200.0)

    spinner = waiting_module.Spinner("payload")
    # Clear any writes that occurred during __init__ (from _supports_unicode)
    fake_out._writes.clear()
    fake_out._flush_called = False

    # Provide a wide console to avoid forced truncation in this test
    spinner.console = FakeConsole(width=200)
    spinner.start_time = 100.0  # ensure now - start_time >= 0.5 so visible will become True

    # Capture the frame that will be used by _next_frame (frame_idx currently pointing to frame to emit)
    pre_frame_idx = spinner.frame_idx
    frame_str = spinner.frames[pre_frame_idx]
    scan_pos = frame_str.find(spinner.scan_char)

    # Call step which should:
    # - set visible True
    # - write "\r" + line_to_display + padding
    # - write backspaces of positive length (in most cases)
    spinner.step()

    # Visible should be True and show_cursor called
    assert spinner.visible is True
    assert spinner.console.show_cursor_calls == [False]

    # Determine expected line_to_display as per code
    current_text_payload = f" {spinner.text}"
    max_spinner_width = spinner.console.width - 2
    line_to_display = f"{frame_str}{current_text_payload}"
    if len(line_to_display) > max_spinner_width:
        line_to_display = line_to_display[:max_spinner_width]

    len_line_to_display = len(line_to_display)
    # padding_to_clear computed from previous last_display_len (which is 0 at init)
    padding_to_clear = " " * max(0, 0 - len_line_to_display)

    # Validate that the captured writes match expectations
    # First write should be the line (with leading '\r')
    assert fake_out.writes[0] == f"\r{line_to_display}{padding_to_clear}"
    # The second write should be the backspaces string
    total_chars_written_on_line = len_line_to_display + len(padding_to_clear)
    expected_backspaces = total_chars_written_on_line - scan_pos
    if expected_backspaces > 0:
        assert fake_out.writes[1] == "\x08" * expected_backspaces
    else:
        assert fake_out.writes[1] == ""

    # Ensure last_display_len updated to the length actually displayed
    assert spinner.last_display_len == len_line_to_display
    # flush should have been called
    assert fake_out.flush_called is True
