# file: openhands/runtime/action_execution_server.py:107-170
# asked: {"lines": [107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 134, 137, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 161, 163, 164, 166, 167, 168, 170], "branches": [[137, 138], [137, 146], [163, 164], [163, 166], [166, 167], [166, 170]]}
# gained: {"lines": [107, 111, 112, 113, 114, 115, 116, 117, 134, 137, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 161, 163, 164, 166, 167, 168, 170], "branches": [[137, 138], [137, 146], [163, 164], [163, 166], [166, 167], [166, 170]]}

import importlib
import types

import pytest


@pytest.fixture
def aes_module():
    # Import the module under test
    mod = importlib.import_module("openhands.runtime.action_execution_server")
    return mod


class SimpleToolResult:
    def __init__(self, output=None, error=None, old_content=None, new_content=None):
        self.output = output
        self.error = error
        self.old_content = old_content
        self.new_content = new_content


class SimpleToolError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def test_invalid_insert_line_string(aes_module):
    _execute = aes_module._execute_file_editor

    # Pass a non-integer string for insert_line to trigger ValueError handling
    out, contents = _execute(
        editor=lambda **kwargs: SimpleToolResult(output="irrelevant"),
        command="do",
        path="/tmp/file",
        insert_line="not_an_int",
    )

    assert out.startswith("ERROR:\nInvalid insert_line value: 'not_an_int'."), "Should report invalid insert_line string"
    assert contents == (None, None)


def test_editor_raises_tool_error(aes_module, monkeypatch):
    _execute = aes_module._execute_file_editor

    # Monkeypatch ToolError and ToolResult in the module to our simple classes
    monkeypatch.setattr(aes_module, "ToolError", SimpleToolError)
    monkeypatch.setattr(aes_module, "ToolResult", SimpleToolResult)

    def editor_raises(**kwargs):
        raise SimpleToolError("tool-failed")

    out, contents = _execute(
        editor=editor_raises,
        command="cmd",
        path="p",
    )

    assert out == "ERROR:\ntool-failed"
    assert contents == (None, None)


def test_editor_raises_type_error(aes_module):
    _execute = aes_module._execute_file_editor

    def editor_typeerror(**kwargs):
        raise TypeError("unexpected keyword arg")

    out, contents = _execute(
        editor=editor_typeerror,
        command="cmd",
        path="p",
    )

    assert out == "ERROR:\nunexpected keyword arg"
    assert contents == (None, None)


def test_result_with_error(aes_module, monkeypatch):
    _execute = aes_module._execute_file_editor

    # Ensure module uses our SimpleToolResult
    monkeypatch.setattr(aes_module, "ToolResult", SimpleToolResult)

    def editor_returns_error(**kwargs):
        return SimpleToolResult(output=None, error="returned-error")

    out, contents = _execute(
        editor=editor_returns_error,
        command="c",
        path="somepath",
    )

    assert out == "ERROR:\nreturned-error"
    assert contents == (None, None)


def test_no_output_logs_warning_and_returns_empty(aes_module, monkeypatch):
    _execute = aes_module._execute_file_editor

    # Provide a fake logger to capture warnings
    warnings = []

    class FakeLogger:
        def warning(self, msg):
            warnings.append(msg)

    monkeypatch.setattr(aes_module, "logger", FakeLogger())
    monkeypatch.setattr(aes_module, "ToolResult", SimpleToolResult)

    def editor_no_output(**kwargs):
        return SimpleToolResult(output="", old_content="old", new_content="new")

    out, contents = _execute(
        editor=editor_no_output,
        command="c",
        path="/some/path",
    )

    assert out == ""
    assert contents == (None, None)
    assert any("/some/path" in w for w in warnings), "Expected a warning mentioning the path"


def test_successful_output_returns_contents(aes_module, monkeypatch):
    _execute = aes_module._execute_file_editor

    monkeypatch.setattr(aes_module, "ToolResult", SimpleToolResult)

    def editor_success(**kwargs):
        return SimpleToolResult(output="OK", old_content="OLD", new_content="NEW")

    out, contents = _execute(
        editor=editor_success,
        command="edit",
        path="file.txt",
    )

    assert out == "OK"
    assert contents == ("OLD", "NEW")
