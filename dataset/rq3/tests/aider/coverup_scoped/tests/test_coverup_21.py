# file: aider/coders/wholefile_func_coder.py:110-134
# asked: {"lines": [110, 111, 112, 113, 115, 116, 117, 119, 121, 122, 123, 124, 125, 127, 128, 129, 131, 132, 134], "branches": [[112, 113], [112, 115], [116, 117], [116, 119], [122, 123], [122, 134], [124, 125], [124, 127], [128, 129], [128, 131], [131, 122], [131, 132]]}
# gained: {"lines": [110, 111, 112, 113, 115, 116, 117, 119, 121, 122, 123, 124, 125, 127, 128, 129, 131, 132, 134], "branches": [[112, 113], [112, 115], [116, 117], [116, 119], [122, 123], [122, 134], [124, 125], [124, 127], [128, 129], [128, 131], [131, 122], [131, 132]]}

import pytest

from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def make_instance():
    # Bypass __init__ which raises RuntimeError
    inst = object.__new__(WholeFileFunctionCoder)
    return inst


def test_update_files_unknown_function_name_raises():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "bad_name"}
    # parse_partial_args should not be called in this branch, but provide one anyway
    inst.parse_partial_args = lambda: {"files": []}
    with pytest.raises(ValueError) as exc:
        inst._update_files()
    assert 'Unknown function_call name="bad_name"' in str(exc.value)
    assert 'use name="write_file"' in str(exc.value)


def test_update_files_no_args_returns_none():
    inst = make_instance()
    # no name provided (or empty), should not raise
    inst.partial_response_function_call = {}
    # parse_partial_args returns falsy -> method returns None
    inst.parse_partial_args = lambda: None
    result = inst._update_files()
    assert result is None


def test_update_files_missing_path_raises():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "write_file"}
    # file dict missing 'path'
    bad_file = {"content": "some content"}
    inst.parse_partial_args = lambda: {"files": [bad_file]}
    with pytest.raises(ValueError) as exc:
        inst._update_files()
    msg = str(exc.value)
    assert "Missing path parameter" in msg
    # representation of the offending dict should be in the message
    assert "content" in msg and "some content" in msg


def test_update_files_missing_content_raises():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "write_file"}
    # file dict missing 'content'
    bad_file = {"path": "a.txt"}
    inst.parse_partial_args = lambda: {"files": [bad_file]}
    with pytest.raises(ValueError) as exc:
        inst._update_files()
    msg = str(exc.value)
    assert "Missing content parameter" in msg
    assert "path" in msg and "a.txt" in msg


def test_update_files_returns_edited_set_respecting_allowed_to_edit():
    inst = make_instance()
    inst.partial_response_function_call = {"name": "write_file"}
    files = [
        {"path": "/allowed1.txt", "content": "content1"},
        {"path": "/denied.txt", "content": "content2"},
        {"path": "/allowed2.txt", "content": "content3"},
    ]
    inst.parse_partial_args = lambda: {"files": files}

    # allowed_to_edit returns True only for paths starting with "/allowed"
    def allowed_to_edit(path, content):
        return path.startswith("/allowed")

    inst.allowed_to_edit = allowed_to_edit

    edited = inst._update_files()
    assert isinstance(edited, set)
    assert edited == {"/allowed1.txt", "/allowed2.txt"}
