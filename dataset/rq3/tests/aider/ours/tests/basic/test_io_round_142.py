import builtins
from unittest.mock import patch
import pytest
import aider.io as aio
from aider.io import InputOutput


class DummyFile:
    def __init__(self, sink):
        self.sink = sink

    def write(self, data):
        # emulate normal file.write
        self.sink.append(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_open_mock(raise_exc_type=None, raise_times=0, sink=None):
    """
    Returns a mock for builtins.open that raises raise_exc_type for the first
    `raise_times` calls, then returns a DummyFile writing into sink.
    """
    counter = {"n": 0}

    def open_mock(filename, mode, encoding=None, newline=None):
        if counter["n"] < raise_times:
            counter["n"] += 1
            raise (raise_exc_type)("simulated")
        return DummyFile(sink)

    return open_mock


def test_write_text_permission_error_backoff_round_142():
    # Simulate PermissionError on the first two attempts, success on third.
    instance = InputOutput.__new__(InputOutput)
    instance.dry_run = False
    instance.encoding = "utf-8"
    instance.newline = ""

    # recorders
    written = []
    sleep_calls = []
    tool_errors = []

    # patch time.sleep used in aider.io to avoid real sleeping and capture delays
    def fake_sleep(delay):
        sleep_calls.append(delay)

    # make open fail twice then succeed
    open_mock = make_open_mock(raise_exc_type=PermissionError, raise_times=2, sink=written)

    # tool_error should not be called when eventual success occurs
    instance.tool_error = lambda msg: tool_errors.append(msg)

    with patch("builtins.open", new=open_mock):
        with patch("aider.io.time.sleep", new=fake_sleep):
            # should succeed and return None (no exception)
            instance.write_text("somefile.txt", "content", max_retries=3, initial_delay=0.1)

    # validate exponential backoff delays: 0.1 then 0.2
    assert sleep_calls == [0.1, 0.2]
    # ensure content was written exactly once to the DummyFile
    assert written == ["content"]
    # ensure no tool_error calls
    assert tool_errors == []


def test_write_text_permission_error_final_failure_round_142():
    # Simulate PermissionError on all attempts to trigger final-tool_error + re-raise
    instance = InputOutput.__new__(InputOutput)
    instance.dry_run = False
    instance.encoding = "utf-8"
    instance.newline = "\n"

    sleep_calls = []
    tool_errors = []

    def fake_sleep(delay):
        sleep_calls.append(delay)

    # open always raises PermissionError
    open_mock = make_open_mock(raise_exc_type=PermissionError, raise_times=5, sink=[])

    instance.tool_error = lambda msg: tool_errors.append(msg)

    with patch("builtins.open", new=open_mock):
        with patch("aider.io.time.sleep", new=fake_sleep):
            with pytest.raises(PermissionError):
                # use max_retries=2 so there will be exactly one sleep then final failure
                instance.write_text("final_fail.txt", "nope", max_retries=2, initial_delay=0.1)

    # one backoff sleep should have happened (attempt 0 -> sleep)
    assert sleep_calls == [0.1]
    # tool_error should have been called once with a message mentioning the filename and attempts
    assert len(tool_errors) == 1
    assert "final_fail.txt" in tool_errors[0]
    assert "2 attempts" in tool_errors[0] or "after 2 attempts" in tool_errors[0]


def test_write_text_oserror_round_142():
    # Simulate an OSError on open to test OSError branch
    instance = InputOutput.__new__(InputOutput)
    instance.dry_run = False
    instance.encoding = "utf-8"
    instance.newline = "\n"

    tool_errors = []

    # open always raises OSError
    open_mock = make_open_mock(raise_exc_type=OSError, raise_times=1, sink=[])

    instance.tool_error = lambda msg: tool_errors.append(msg)

    with patch("builtins.open", new=open_mock):
        with pytest.raises(OSError):
            instance.write_text("osfail.txt", "x", max_retries=1, initial_delay=0.1)

    # OSError path should call tool_error once and re-raise
    assert len(tool_errors) == 1
    assert "osfail.txt" in tool_errors[0]
