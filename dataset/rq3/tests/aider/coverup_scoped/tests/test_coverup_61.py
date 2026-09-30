# file: aider/io.py:453-476
# asked: {"lines": [465, 466, 467, 469, 470, 471], "branches": [[461, 463], [465, 466], [465, 467], [469, 470], [469, 471], [473, 476]]}
# gained: {"lines": [465, 466, 467, 469, 470, 471], "branches": [[461, 463], [465, 466], [469, 470]]}

import builtins
import pytest
from aider.io import InputOutput


class DummyIO(InputOutput):
    # Use default behavior but allow setting a custom tool_error
    pass


def _make_io():
    io = DummyIO()
    # Ensure encoding attribute exists
    io.encoding = "utf-8"
    return io


def test_read_text_file_not_found_calls_tool_error_and_respects_silent(monkeypatch):
    filename = "missing.txt"

    def raising_open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("builtins.open", raising_open)

    io = _make_io()
    messages = []

    io.tool_error = lambda msg: messages.append(msg)

    # silent=False -> should call tool_error
    result = io.read_text(filename, silent=False)
    assert result is None
    assert messages == [f"{filename}: file not found error"]

    # silent=True -> should NOT call tool_error
    messages.clear()
    result = io.read_text(filename, silent=True)
    assert result is None
    assert messages == []


def test_read_text_is_directory_calls_tool_error(monkeypatch):
    filename = "some_dir"

    def raising_open(*args, **kwargs):
        raise IsADirectoryError

    monkeypatch.setattr("builtins.open", raising_open)

    io = _make_io()
    messages = []
    io.tool_error = lambda msg: messages.append(msg)

    result = io.read_text(filename, silent=False)
    assert result is None
    assert messages == [f"{filename}: is a directory"]


def test_read_text_oserror_calls_tool_error(monkeypatch):
    filename = "badfile.txt"

    def raising_open(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("builtins.open", raising_open)

    io = _make_io()
    messages = []
    io.tool_error = lambda msg: messages.append(msg)

    result = io.read_text(filename, silent=False)
    assert result is None
    assert len(messages) == 1
    assert messages[0].startswith(f"{filename}: unable to read:")
    assert "boom" in messages[0]


def test_read_text_unicode_error_calls_tool_error_twice(monkeypatch):
    filename = "weird_encoding.txt"

    def raising_open(*args, **kwargs):
        # UnicodeDecodeError(encoding, object, start, end, reason)
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

    monkeypatch.setattr("builtins.open", raising_open)

    io = _make_io()
    messages = []
    io.tool_error = lambda msg: messages.append(msg)

    result = io.read_text(filename, silent=False)
    assert result is None
    # Expect two messages: one with the filename and error, one suggesting encoding flag
    assert len(messages) == 2
    assert filename in messages[0]
    assert "invalid start byte" in messages[0]
    assert messages[1] == "Use --encoding to set the unicode encoding."
