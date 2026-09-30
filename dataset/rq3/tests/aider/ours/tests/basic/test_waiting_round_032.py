import sys
import types
import pytest

from aider.waiting import Spinner


class FakeStdOut:
    def __init__(self):
        self.writes = []
        self.flushed = 0

    def write(self, data):
        # capture every write call (including empty strings)
        self.writes.append(data)

    def flush(self):
        self.flushed += 1


class FakeConsole:
    def __init__(self, width):
        self.width = width
        self.show_cursor_calls = []

    def show_cursor(self, flag):
        self.show_cursor_calls.append(flag)


def _install_fake_stdout(monkeypatch):
    fake = FakeStdOut()
    monkeypatch.setattr(sys, "stdout", fake)
    return fake


def test_non_tty_returns_round_032(monkeypatch):
    """
    When the spinner is not a TTY, step should return early and not write to stdout.
    This covers the early-return branch at lines 109-110.
    """
    spinner = Spinner("orig", width=10)

    # Ensure spinner will think it's not a tty
    spinner.is_tty = False

    fake_out = _install_fake_stdout(monkeypatch)

    # Call step with new text to confirm text update happens but no stdout writes
    spinner.step("updated")

    assert spinner.text == "updated"
    # No writes should have been made to stdout
    assert fake_out.writes == []


def test_small_width_truncate_round_032(monkeypatch):
    """
    Force console width so max_spinner_width < 0 path (line 128) is taken.
    Ensure the line is fully truncated, padding_to_clear is used, and zero backspaces
    are written when the scan character is exactly at the boundary (num_backspaces == 0).
    This exercises toggling visible -> True, show_cursor being called, truncation, and
    the num_backspaces == 0 case around lines 112-122, 128-136, 140-159.
    """
    spinner = Spinner("payload", width=10)

    # Replace console with very narrow console to trigger max_spinner_width < 0
    fake_console = FakeConsole(width=1)
    spinner.console = fake_console

    # Make sure spinner behaves as TTY and is currently not visible so visible gets toggled
    spinner.is_tty = True
    spinner.visible = False

    # Make start_time sufficiently in the past so visible will flip on this step
    now = 1000.0
    spinner.start_time = now - 1.0

    # Ensure a previous longer display existed so padding clearing path is exercised
    spinner.last_display_len = 5

    # Provide a frame where the scan_char is at index 5 (0-based) so num_backspaces = total - 5
    # We'll make total_chars_written_on_line = padding(5) + len_line_to_display(0) => 5
    # So scan_char_abs_pos == 5 -> num_backspaces == 0 (non-positive branch)
    frame_with_scan_at_5 = "xxxxx#"
    spinner.scan_char = "#"
    monkeypatch.setattr(spinner, "_next_frame", lambda: frame_with_scan_at_5)

    # Patch time.time to return our controlled value
    monkeypatch.setattr("time.time", lambda: now)

    fake_out = _install_fake_stdout(monkeypatch)

    # Call step without passing text to avoid changing spinner.text beyond initialization
    spinner.step()

    # After toggling visible, console.show_cursor(False) should have been called once
    assert fake_console.show_cursor_calls == [False]

    # Because max_spinner_width becomes 0 the constructed line is truncated to ""
    # First write should be the carriage return + padding_to_clear (5 spaces)
    assert fake_out.writes[0] == "\r" + " " * 5

    # The next write is backspaces repeated num_backspaces times; in our arrangement num_backspaces == 0
    # so an empty string write is expected and should be captured
    # (the code does sys.stdout.write("\b" * 0) which calls write with "")
    assert fake_out.writes[1] == ""

    # last_update should be set to now (the code updates last_update before writing)
    assert spinner.last_update == pytest.approx(now)


def test_no_truncate_and_backspaces_positive_round_032(monkeypatch):
    """
    Exercise the path where no truncation occurs, no visible-toggle is needed, and
    a positive number of backspaces are written to position the cursor on the scan char.
    This covers the branches around lines 122-139 and 147-160.
    """
    spinner = Spinner("ok", width=80)

    # Wide console so no truncation
    fake_console = FakeConsole(width=80)
    spinner.console = fake_console

    spinner.is_tty = True
    # Already visible so the visible-toggle branch (show_cursor) is not executed
    spinner.visible = True

    # Set last_update sufficiently in the past so update proceeds
    now = 2000.0
    spinner.last_update = now - 1.0

    # frame where scan_char is at position 0
    spinner.scan_char = "*"
    monkeypatch.setattr(spinner, "_next_frame", lambda: "*")

    # Ensure time.time returns our now
    monkeypatch.setattr("time.time", lambda: now)

    fake_out = _install_fake_stdout(monkeypatch)

    # Call step; since visible is True and now - last_update >= 0.1 update proceeds
    spinner.step("text")

    # The first write should include the carriage return and the full line
    # Construct expected line: frame_str ('*') + ' ' + spinner.text
    expected_line = "*" + " " + spinner.text
    assert fake_out.writes[0] == "\r" + expected_line

    # Compute expected backspaces: total_chars_written_on_line = len_line_to_display (no padding) 
    len_line = len(expected_line)
    expected_backspaces = "\b" * (len_line - expected_line.find(spinner.scan_char))

    # Second write contains that many backspaces
    assert fake_out.writes[1] == expected_backspaces

    # last_display_len should be updated to the length of the displayed line
    assert spinner.last_display_len == len_line

    # console.show_cursor should not have been called in this path
    assert fake_console.show_cursor_calls == []
