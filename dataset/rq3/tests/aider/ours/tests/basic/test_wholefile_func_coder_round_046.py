import pytest

from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def _make_coder():
    # Create instance without running __init__ to avoid external dependencies
    return object.__new__(WholeFileFunctionCoder)


def test_unknown_function_name_round_046():
    coder = _make_coder()
    # simulate a function call name that is not allowed
    coder.partial_response_function_call = {"name": "bad_name"}

    # parse_partial_args should not be required to be called for this branch,
    # but provide a harmless stub to be safe
    coder.parse_partial_args = lambda: {"files": []}

    with pytest.raises(ValueError) as exc:
        coder._update_files()

    assert str(exc.value) == 'Unknown function_call name="bad_name", use name="write_file"'


def test_no_args_returns_none_round_046():
    coder = _make_coder()
    # no name provided (None) and parse_partial_args returns falsy -> early return
    coder.partial_response_function_call = {}
    coder.parse_partial_args = lambda: None

    result = coder._update_files()
    assert result is None


def test_empty_files_key_returns_empty_set_round_046():
    coder = _make_coder()
    coder.partial_response_function_call = {"name": "write_file"}
    # args truthy but files empty list -> should return an empty set
    coder.parse_partial_args = lambda: {"files": []}

    result = coder._update_files()
    assert isinstance(result, set)
    assert result == set()


def test_missing_path_raises_round_046():
    coder = _make_coder()
    coder.partial_response_function_call = {"name": "write_file"}
    # file dict missing 'path'
    file_upd = {"content": "some content"}
    coder.parse_partial_args = lambda: {"files": [file_upd]}

    with pytest.raises(ValueError) as exc:
        coder._update_files()

    # error message includes the exact dict representation
    assert str(exc.value) == f"Missing path parameter: {file_upd}"


def test_missing_content_raises_round_046():
    coder = _make_coder()
    coder.partial_response_function_call = {"name": "write_file"}
    # file dict missing 'content'
    file_upd = {"path": "some/path.txt"}
    coder.parse_partial_args = lambda: {"files": [file_upd]}

    with pytest.raises(ValueError) as exc:
        coder._update_files()

    assert str(exc.value) == f"Missing content parameter: {file_upd}"


def test_allowed_to_edit_adds_paths_round_046():
    coder = _make_coder()
    coder.partial_response_function_call = {"name": "write_file"}

    files = [
        {"path": "allowed.txt", "content": "ok"},
        {"path": "blocked.txt", "content": "no"},
    ]
    coder.parse_partial_args = lambda: {"files": files}

    # allow editing only the first path
    def allowed_to_edit(path, content):
        return path == "allowed.txt"

    coder.allowed_to_edit = allowed_to_edit

    result = coder._update_files()
    assert result == {"allowed.txt"}
