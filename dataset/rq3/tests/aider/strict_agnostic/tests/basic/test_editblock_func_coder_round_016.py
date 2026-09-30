import pytest
from aider.coders import editblock_func_coder as module
from aider.coders.editblock_func_coder import EditBlockFunctionCoder


class FakeIO:
    def __init__(self, read_return=""):
        self.read_calls = []
        self.read_return = read_return
        self.written = []
        self.tool_errors = []

    def read_text(self, path):
        self.read_calls.append(path)
        return self.read_return

    def write_text(self, path, content):
        self.written.append((path, content))

    def tool_error(self, msg):
        self.tool_errors.append(msg)


def make_coder(code_format="str"):
    # Create instance without running __init__ to avoid side effects
    coder = object.__new__(EditBlockFunctionCoder)
    # Set minimal attributes used by _update_files
    coder.code_format = code_format
    coder.partial_response_function_call = {}
    # defaults; tests will override as needed
    coder.parse_partial_args = lambda: {}
    coder.allowed_to_edit = lambda p: False
    coder.io = FakeIO()
    return coder


def test_unknown_function_call_name_round_016():
    coder = make_coder()
    coder.partial_response_function_call = {"name": "bad_name"}

    with pytest.raises(ValueError) as excinfo:
        coder._update_files()

    assert 'Unknown function_call name="bad_name", use name="replace_lines"' in str(excinfo.value)


def test_no_args_round_016():
    coder = make_coder()
    coder.partial_response_function_call = {}

    # parse_partial_args returns an empty dict (falsy) -> method should return None
    coder.parse_partial_args = lambda: {}

    result = coder._update_files()

    assert result is None
    # ensure no IO interactions
    assert coder.io.read_calls == []
    assert coder.io.written == []
    assert coder.io.tool_errors == []


def test_successful_edit_write_round_016(monkeypatch):
    # Test path where edits are applied, lists are joined, newlines appended, and write_text is called
    coder = make_coder(code_format="list")
    coder.partial_response_function_call = {}

    # One edit: original/updated as lists to trigger join branch
    edit = {"path": "a.py", "original_lines": ["old_line"], "updated_lines": ["new_line"]}
    coder.parse_partial_args = lambda: {"edits": [edit]}

    # allowed_to_edit returns an absolute path
    coder.allowed_to_edit = lambda p: "/abs/" + p

    # simulate file content read
    coder.io = FakeIO(read_return="some file content")

    # patch module.do_replace to assert inputs and return a non-empty string to trigger write
    def fake_do_replace(full_path, content, original, updated):
        # confirm full_path came from allowed_to_edit
        assert full_path == "/abs/a.py"
        # because code_format == "list", original and updated should be joined strings
        assert isinstance(original, str) and isinstance(updated, str)
        # newline should be appended by the method
        assert original.endswith("\n")
        assert updated.endswith("\n")
        # return new content to cause write_text
        return "replaced content"

    monkeypatch.setattr(module, "do_replace", fake_do_replace)

    edited = coder._update_files()

    assert edited == {"a.py"}
    # ensure write_text was called with path and replaced content
    assert coder.io.written == [("/abs/a.py", "replaced content")]
    assert coder.io.tool_errors == []


def test_failed_replace_calls_tool_error_round_016(monkeypatch):
    # When do_replace returns falsy, tool_error should be invoked and nothing written
    coder = make_coder(code_format="str")
    coder.partial_response_function_call = {}

    edit = {"path": "b.py", "original_lines": "orig", "updated_lines": "upd"}
    coder.parse_partial_args = lambda: {"edits": [edit]}
    coder.allowed_to_edit = lambda p: "/abs/" + p
    coder.io = FakeIO(read_return="file content")

    def fake_do_replace(full_path, content, original, updated):
        # simulate failure to apply edit
        return ""  # falsy -> should call tool_error

    monkeypatch.setattr(module, "do_replace", fake_do_replace)

    edited = coder._update_files()

    assert edited == set()
    # tool_error should have been called with expected message
    assert any("Failed to apply edit to b.py" in msg for msg in coder.io.tool_errors)
    # nothing should have been written
    assert coder.io.written == []


def test_skip_not_allowed_edit_round_016():
    # If allowed_to_edit returns falsy, the edit is skipped and no IO happens
    coder = make_coder()
    coder.partial_response_function_call = {}

    edit = {"path": "skip.py", "original_lines": "x", "updated_lines": "y"}
    coder.parse_partial_args = lambda: {"edits": [edit]}
    coder.allowed_to_edit = lambda p: False
    coder.io = FakeIO(read_return="unused")

    edited = coder._update_files()

    assert edited == set()
    assert coder.io.read_calls == []
    assert coder.io.written == []
    assert coder.io.tool_errors == []
