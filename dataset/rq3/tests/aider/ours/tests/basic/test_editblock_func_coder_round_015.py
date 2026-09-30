import importlib
import pytest


class FakeIO:
    def __init__(self):
        self.writes = []
        self.tool_errors = []
        self.read_calls = []

    def read_text(self, path):
        self.read_calls.append(path)
        return "original content"

    def write_text(self, path, content):
        self.writes.append((path, content))

    def tool_error(self, msg):
        self.tool_errors.append(msg)


def _get_module():
    return importlib.import_module("aider.coders.editblock_func_coder")


def _make_instance(mod, code_format="text"):
    C = mod.EditBlockFunctionCoder
    inst = object.__new__(C)
    # set the attributes used by _update_files
    inst.partial_response_function_call = {}
    inst.parse_partial_args = lambda: {}
    inst.code_format = code_format
    inst.allowed_to_edit = lambda p: None
    inst.io = FakeIO()
    return inst


def test_unknown_name_round_015():
    """If partial_response_function_call has a name other than 'replace_lines', a ValueError is raised."""
    mod = _get_module()
    inst = _make_instance(mod)

    inst.partial_response_function_call = {"name": "not_replace"}

    with pytest.raises(ValueError) as exc:
        inst._update_files()

    assert 'Unknown function_call name="not_replace"' in str(exc.value)


def test_no_args_round_015():
    """When parse_partial_args returns falsy, _update_files returns None (no edits applied)."""
    mod = _get_module()
    inst = _make_instance(mod)

    # simulate parse_partial_args returning empty mapping
    inst.parse_partial_args = lambda: {}

    result = inst._update_files()

    assert result is None


def test_apply_edit_writes_round_015():
    """A single edit that is allowed_to_edit and where do_replace returns content should cause a write and return the edited path."""
    mod = _get_module()
    inst = _make_instance(mod)

    # Ensure get_arg simply reads dict keys
    mod.get_arg = lambda edit, key: edit.get(key)

    # One edit as plain strings (will exercise newline-appending behavior)
    inst.parse_partial_args = lambda: {
        "edits": [
            {"path": "package/file.py", "original_lines": "orig_line", "updated_lines": "new_line"}
        ]
    }
    inst.partial_response_function_call = {}
    inst.code_format = "text"

    # allowed_to_edit returns a full path (truthy) so edit proceeds
    inst.allowed_to_edit = lambda p: f"/full/{p}"

    fake_io = FakeIO()
    inst.io = fake_io

    # Simulate do_replace producing new content -> should trigger write_text and addition to edited set
    def fake_do_replace(full_path, content, original, updated):
        # original/updated should have trailing newline appended by _update_files
        assert original.endswith("\n")
        assert updated.endswith("\n")
        return "replaced content"

    mod.do_replace = fake_do_replace

    edited = inst._update_files()

    assert edited == {"package/file.py"}
    assert fake_io.writes == [("/full/package/file.py", "replaced content")]
    assert fake_io.tool_errors == []


def test_edit_failed_round_015():
    """When do_replace returns falsy, io.tool_error is called and the path is not included in the edited set."""
    mod = _get_module()
    # create instance bypassing __init__ and set code_format to text (list type behavior exercised via list args)
    inst = _make_instance(mod, code_format="text")

    # Ensure get_arg simply reads dict keys
    mod.get_arg = lambda edit, key: edit.get(key)

    # Use list-typed original/updated to exercise the join-to-string branch
    inst.parse_partial_args = lambda: {
        "edits": [
            {"path": "package/broken.py", "original_lines": ["a"], "updated_lines": ["b"]}
        ]
    }
    inst.partial_response_function_call = {}

    inst.allowed_to_edit = lambda p: f"/full/{p}"
    fake_io = FakeIO()
    inst.io = fake_io

    # do_replace returns empty string (falsy) -> should call tool_error
    mod.do_replace = lambda full_path, content, original, updated: ""

    edited = inst._update_files()

    # No edits applied
    assert edited == set()

    # Ensure tool_error was invoked with the expected message
    assert any("Failed to apply edit to package/broken.py" in m for m in fake_io.tool_errors)
