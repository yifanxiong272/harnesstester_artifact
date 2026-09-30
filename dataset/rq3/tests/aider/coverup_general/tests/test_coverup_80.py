# file: aider/io.py:478-507
# asked: {"lines": [496, 497, 498, 499, 501, 502, 504, 505, 506, 507], "branches": [[491, 0], [497, 498], [497, 501]]}
# gained: {"lines": [496, 497, 498, 499, 501, 502, 504, 505, 506, 507], "branches": [[497, 498], [497, 501]]}

import builtins
import io
import os
import time
import pytest

from aider.io import InputOutput


class DummyIO(InputOutput):
    def __init__(self):
        # don't call super().__init__ to avoid unknown requirements; set needed attributes
        self.dry_run = False
        self.encoding = "utf-8"
        self.newline = ""
        self.tool_errors = []

    def tool_error(self, msg):
        self.tool_errors.append(msg)


def test_write_text_success(tmp_path):
    # Test that a normal write returns and file contains expected content (covers loop exit via return).
    filename = tmp_path / "out.txt"
    content = "hello world\n"

    ioobj = DummyIO()
    # Use real open to write to a real temporary file.
    ioobj.write_text(filename, content)

    # Verify file written correctly
    with open(filename, "r", encoding=ioobj.encoding, newline=ioobj.newline) as f:
        read = f.read()
    assert read == content
    # tool_error should not have been called
    assert ioobj.tool_errors == []


def test_write_text_permission_retries_then_raise(monkeypatch):
    # Simulate PermissionError on every attempt and ensure it retries max_retries times,
    # calls tool_error with expected message, and finally re-raises PermissionError.
    calls = {"count": 0}

    def fake_open(*args, **kwargs):
        calls["count"] += 1
        raise PermissionError("file locked")

    monkeypatch.setattr(builtins, "open", fake_open)
    # make sleep a no-op to avoid slow tests and to record if it was called
    slept = []

    def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    ioobj = DummyIO()
    filename = "somefile.txt"
    max_retries = 3
    # Expect PermissionError after exhausting retries
    with pytest.raises(PermissionError):
        ioobj.write_text(filename, "x", max_retries=max_retries, initial_delay=0.01)

    # open should have been called max_retries times
    assert calls["count"] == max_retries
    # sleep should have been called max_retries - 1 times (between failed attempts)
    assert len(slept) == max_retries - 1
    # tool_error should have been called once with the expected message content
    assert len(ioobj.tool_errors) == 1
    assert f"Unable to write file {filename} after {max_retries} attempts" in ioobj.tool_errors[0]


def test_write_text_permission_then_success(monkeypatch, tmp_path):
    # Simulate a PermissionError on the first attempt, then success on the second.
    calls = {"count": 0}
    written = {"content": None, "path": None}
    initial_delay = 0.02

    class FakeFile(io.StringIO):
        def __init__(self):
            super().__init__()
            # emulate context manager real file
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            self.seek(0)
            return False

    def fake_open(path, mode="r", encoding=None, newline=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("locked on first try")
        # on second call, return a fake file object whose write stores content for assertion
        f = FakeFile()
        # monkeypatch the write to capture content
        orig_write = f.write

        def write_and_capture(data):
            written["content"] = (written.get("content") or "") + data
            orig_write(data)

        f.write = write_and_capture
        return f

    slept = []

    def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    ioobj = DummyIO()
    filename = tmp_path / "two_try.txt"
    content = "recovered content"

    # Should not raise
    ioobj.write_text(filename, content, max_retries=3, initial_delay=initial_delay)

    # Verify it retried once then succeeded
    assert calls["count"] == 2
    assert written["content"] == content
    # sleep should have been called once with the initial delay
    assert slept and pytest.approx(slept[0], rel=1e-3) == initial_delay
    # No tool_error calls
    assert ioobj.tool_errors == []


def test_write_text_oserror_calls_tool_error_and_raises(monkeypatch):
    # Simulate an OSError on open and ensure tool_error is called and OSError is re-raised.
    calls = {"count": 0}

    def fake_open(*args, **kwargs):
        calls["count"] += 1
        raise OSError("disk full")

    monkeypatch.setattr(builtins, "open", fake_open)

    ioobj = DummyIO()
    filename = "broken.txt"
    with pytest.raises(OSError):
        ioobj.write_text(filename, "data", max_retries=2)

    # open should have been called exactly once (OSError isn't retried)
    assert calls["count"] == 1
    # tool_error should have been called once with the OSError message
    assert len(ioobj.tool_errors) == 1
    assert "Unable to write file broken.txt" in ioobj.tool_errors[0]
    assert "disk full" in ioobj.tool_errors[0]
