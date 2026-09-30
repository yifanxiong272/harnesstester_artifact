import importlib
from types import SimpleNamespace

import pytest

io_mod = importlib.import_module('aider.io')
InputOutput = io_mod.InputOutput


def test_returns_early_when_no_file_round_143(monkeypatch):
    """If input_history_file is falsy, FileHistory must not be invoked and method returns quickly."""
    # Patch FileHistory to fail if called (ensures early return)
    def _bad_filehistory(*args, **kwargs):
        raise AssertionError("FileHistory was called despite no input_history_file")

    monkeypatch.setattr(io_mod, 'FileHistory', _bad_filehistory)

    inst = object.__new__(InputOutput)
    inst.input_history_file = None  # falsy -> should return immediately

    # tool_warning should not be invoked; record if it is
    warnings = []

    def tool_warning(msg):
        warnings.append(msg)

    inst.tool_warning = tool_warning
    # No prompt_session set

    # Should not raise and should not add warnings
    inst.add_to_input_history("some input")
    assert warnings == []


def test_appends_to_file_and_prompt_history_round_143(monkeypatch):
    """When input_history_file is set, FileHistory.append_string and prompt_session.history.append_string are called."""
    file_calls = []
    session_calls = []
    warnings = []

    class MockFileHistory:
        def __init__(self, path):
            # record that it was constructed with provided path
            self.path = path

        def append_string(self, s):
            file_calls.append((self.path, s))

    # Patch the FileHistory used in the module under test
    monkeypatch.setattr(io_mod, 'FileHistory', MockFileHistory)

    inst = object.__new__(InputOutput)
    inst.input_history_file = "/fake/path"

    # prompt_session.history must exist and have append_string
    history_obj = SimpleNamespace()

    def history_append(s):
        session_calls.append(s)

    history_obj.append_string = history_append
    inst.prompt_session = SimpleNamespace(history=history_obj)

    def tool_warning(msg):
        warnings.append(msg)

    inst.tool_warning = tool_warning

    inst.add_to_input_history("hello world")

    # FileHistory constructed and append_string called with provided input
    assert file_calls == [("/fake/path", "hello world")]
    # prompt_session.history.append_string called
    assert session_calls == ["hello world"]
    # no warnings should have been emitted
    assert warnings == []


def test_oserror_calls_tool_warning_round_143(monkeypatch):
    """If FileHistory.append_string raises OSError, tool_warning is called with the error message."""
    warnings = []

    class BadFileHistory:
        def __init__(self, path):
            self.path = path

        def append_string(self, s):
            raise OSError("disk full")

    monkeypatch.setattr(io_mod, 'FileHistory', BadFileHistory)

    inst = object.__new__(InputOutput)
    inst.input_history_file = "/fake/path"
    # No prompt_session to ensure only file error path is used
    inst.prompt_session = None

    def tool_warning(msg):
        warnings.append(msg)

    inst.tool_warning = tool_warning

    # Should not raise; should capture the OSError and call tool_warning
    inst.add_to_input_history("irrelevant")

    assert len(warnings) == 1
    assert "Unable to write to input history file:" in warnings[0]
    assert "disk full" in warnings[0]
