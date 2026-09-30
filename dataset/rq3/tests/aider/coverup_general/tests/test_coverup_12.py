# file: aider/coders/editblock_func_coder.py:95-135
# asked: {"lines": [95, 96, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 111, 114, 115, 116, 117, 119, 120, 121, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 135], "branches": [[98, 99], [98, 101], [102, 103], [102, 105], [108, 109], [108, 135], [114, 115], [114, 116], [116, 117], [116, 119], [119, 120], [119, 121], [121, 122], [121, 124], [125, 126], [125, 127], [129, 130], [129, 133]]}
# gained: {"lines": [95, 96, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 111, 114, 115, 116, 117, 119, 120, 121, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 135], "branches": [[98, 99], [98, 101], [102, 103], [102, 105], [108, 109], [108, 135], [114, 115], [116, 117], [119, 120], [121, 122], [125, 126], [125, 127], [129, 130], [129, 133]]}

import pytest
import importlib

mod = importlib.import_module("aider.coders.editblock_func_coder")
EditBlockFunctionCoder = getattr(mod, "EditBlockFunctionCoder")


class DummyIO:
    def __init__(self):
        self.read_calls = []
        self.write_calls = []
        self.tool_errors = []

    def read_text(self, path):
        self.read_calls.append(path)
        # Return some dummy content; specific content doesn't matter because do_replace is monkeypatched
        return "original file content\n"

    def write_text(self, path, content):
        self.write_calls.append((path, content))

    def tool_error(self, msg):
        self.tool_errors.append(msg)


def make_instance():
    # Bypass __init__
    inst = object.__new__(EditBlockFunctionCoder)
    return inst


def test_unknown_function_name_raises_value_error():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "not_replace_lines"}
    # parse_partial_args should not be called because error raised first, but set anyway
    inst.parse_partial_args = lambda: {"edits": []}

    with pytest.raises(ValueError) as exc:
        inst._update_files()
    assert 'Unknown function_call name="not_replace_lines"' in str(exc.value)


def test_parse_partial_args_empty_returns_none():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "replace_lines"}
    # simulate empty parse result
    inst.parse_partial_args = lambda: {}
    # need other attributes not used in this branch, but set to defaults
    inst.code_format = "list"
    inst.io = DummyIO()
    inst.allowed_to_edit = lambda path: None

    result = inst._update_files()
    assert result is None


def test_allowed_to_edit_skips_edits_and_no_io_calls():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "replace_lines"}
    inst.parse_partial_args = lambda: {
        "edits": [
            {"path": "skip.py", "original_lines": ["a"], "updated_lines": ["b"]}
        ]
    }
    inst.code_format = "list"
    io = DummyIO()
    inst.io = io
    # disallow editing
    inst.allowed_to_edit = lambda path: None

    edited = inst._update_files()
    # No files edited
    assert edited == set()
    # read_text/write_text/tool_error should not be called
    assert io.read_calls == []
    assert io.write_calls == []
    assert io.tool_errors == []


def test_successful_and_failed_edits(monkeypatch):
    inst = make_instance()
    inst.partial_response_function_call = {"name": "replace_lines"}
    # Two edits: one will succeed, one will fail
    edits = [
        {
            "path": "good.py",
            # provide lists to trigger joining logic
            "original_lines": ["line1"],
            "updated_lines": ["line1_modified"],
        },
        {
            "path": "bad.py",
            # provide lists to test list handling as well
            "original_lines": ["x"],
            "updated_lines": ["y"],
        },
    ]
    inst.parse_partial_args = lambda: {"edits": edits}
    inst.code_format = "list"

    io = DummyIO()
    inst.io = io

    # allowed_to_edit returns a filesystem-like full path for allowed files; emulate skipping or allowing
    def allowed_to_edit(path):
        # allow both; return some full path string
        return f"/full/{path}"

    inst.allowed_to_edit = allowed_to_edit

    # Prepare do_replace monkeypatch: succeed for good.py, fail for bad.py
    def fake_do_replace(full_path, content, original, updated):
        # Check that newline was appended when necessary
        assert original.endswith("\n")
        assert updated.endswith("\n")
        if full_path.endswith("good.py"):
            # return some new content to trigger write_text
            return "file content after edit\n"
        elif full_path.endswith("bad.py"):
            # return '' to indicate failure to apply edit
            return ""
        else:
            return None

    monkeypatch.setattr(mod, "do_replace", fake_do_replace)

    edited = inst._update_files()

    # Ensure good.py was recorded as edited, bad.py not
    assert edited == {"good.py"}

    # write_text should have been called once for good.py with new content
    assert len(io.write_calls) == 1
    written_path, written_content = io.write_calls[0]
    assert written_path == "/full/good.py"
    assert written_content == "file content after edit\n"

    # read_text should have been called for both full paths
    assert "/full/good.py" in io.read_calls
    assert "/full/bad.py" in io.read_calls

    # tool_error should have been called for bad.py
    assert any("Failed to apply edit to bad.py" in msg for msg in io.tool_errors)
