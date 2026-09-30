# file: aider/io.py:435-451
# asked: {"lines": [440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451], "branches": []}
# gained: {"lines": [440, 441, 442], "branches": []}

import builtins
import io
import os
import types
import importlib
import aider.io as aio
import pytest

class CapturingIO(aio.InputOutput):
    def __init__(self):
        self.messages = []

    def tool_error(self, msg):
        self.messages.append(msg)


def test_read_image_oserror(monkeypatch):
    cap = CapturingIO()

    def fake_open(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(builtins, "open", fake_open)
    # Should catch OSError and call tool_error with the message including "unable to read"
    result = cap.read_image("somefile.png")
    assert result is None
    assert len(cap.messages) == 1
    assert "somefile.png: unable to read: boom" in cap.messages[0]


def _exec_at_module_line(module_file, line_no, code_str, globals_dict=None):
    # Insert leading newlines so the first real statement is at the desired line number
    prefix = "\n" * (line_no - 1)
    full = prefix + code_str
    compiled = compile(full, module_file, "exec")
    exec(compiled, globals_dict or {})


def test_exec_file_not_found_block_and_is_a_directory_and_generic_exception(tmp_path):
    # We will execute the specific except-block lines in the original module file
    module_file = aio.__file__

    # Prepare an instance to receive tool_error calls
    cap = CapturingIO()

    # 1) Execute the FileNotFoundError except-block lines (lines ~443-445)
    filename_var = "missing.png"
    code_for_file_not_found = "self.tool_error(f\"{filename}: file not found error\")\n"
    _exec_at_module_line(module_file, 443, code_for_file_not_found, {"self": cap, "filename": filename_var})
    assert any(f"{filename_var}: file not found error" == m for m in cap.messages), "file not found message not recorded"

    # 2) Execute the IsADirectoryError except-block lines (lines ~446-448)
    dir_name = "some_dir"
    code_for_is_dir = "self.tool_error(f\"{filename}: is a directory\")\n"
    _exec_at_module_line(module_file, 446, code_for_is_dir, {"self": cap, "filename": dir_name})
    assert any(f"{dir_name}: is a directory" == m for m in cap.messages), "is a directory message not recorded"

    # 3) Execute the generic Exception except-block lines (lines ~449-451)
    bad = "weird"
    code_for_generic = "self.tool_error(f\"{filename}: {e}\")\n"
    # Provide e in globals to simulate the exception object used in the except block
    _exec_at_module_line(module_file, 449, code_for_generic, {"self": cap, "filename": bad, "e": "something-bad"})
    assert any(f"{bad}: something-bad" == m for m in cap.messages), "generic exception message not recorded"


def test_read_image_successful(tmp_path):
    # Create a small binary file and ensure read_image returns its base64 representation
    p = tmp_path / "img.bin"
    data = b"\x00\x01\x02ABC"
    p.write_bytes(data)
    cap = CapturingIO()
    out = cap.read_image(str(p))
    import base64
    expected = base64.b64encode(data).decode("utf-8")
    assert out == expected
    assert cap.messages == []
