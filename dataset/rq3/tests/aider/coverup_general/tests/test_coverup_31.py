# file: aider/coders/wholefile_func_coder.py:110-134
# asked: {"lines": [110, 111, 112, 113, 115, 116, 117, 119, 121, 122, 123, 124, 125, 127, 128, 129, 131, 132, 134], "branches": [[112, 113], [112, 115], [116, 117], [116, 119], [122, 123], [122, 134], [124, 125], [124, 127], [128, 129], [128, 131], [131, 122], [131, 132]]}
# gained: {"lines": [110, 111, 112, 113, 115, 116, 117, 119, 121, 122, 123, 124, 125, 127, 128, 129, 131, 132, 134], "branches": [[112, 113], [112, 115], [116, 117], [116, 119], [122, 123], [122, 134], [124, 125], [124, 127], [128, 129], [128, 131], [131, 122], [131, 132]]}

import pytest
from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def _make_instance(partial_call=None, parse_args_fn=None, allowed_fn=None):
    # Create instance without calling __init__
    inst = object.__new__(WholeFileFunctionCoder)
    # required attribute used by _update_files
    inst.partial_response_function_call = partial_call if partial_call is not None else {}
    # parse_partial_args should be a callable taking no args
    if parse_args_fn is not None:
        inst.parse_partial_args = parse_args_fn
    else:
        inst.parse_partial_args = lambda: {}
    # allowed_to_edit should be a callable taking (path, content)
    if allowed_fn is not None:
        inst.allowed_to_edit = allowed_fn
    else:
        inst.allowed_to_edit = lambda path, content: True
    return inst


def test_update_files_raises_on_unknown_name():
    inst = _make_instance(
        partial_call={"name": "not_write_file"},
        parse_args_fn=lambda: {"files": [{"path": "a", "content": "b"}]},
    )

    with pytest.raises(ValueError) as exc:
        inst._update_files()
    assert 'Unknown function_call name="not_write_file"' in str(exc.value)


def test_update_files_returns_none_on_no_args():
    # parse_partial_args returns empty dict -> falsy -> early return
    inst = _make_instance(
        partial_call={}, parse_args_fn=lambda: {}
    )
    result = inst._update_files()
    assert result is None


def test_update_files_raises_when_missing_path():
    inst = _make_instance(
        partial_call={}, parse_args_fn=lambda: {"files": [{"content": "x"}]}
    )
    with pytest.raises(ValueError) as exc:
        inst._update_files()
    assert "Missing path parameter" in str(exc.value)
    # ensure the offending file dict is included in the message
    assert "{'content': 'x'}" in str(exc.value)


def test_update_files_raises_when_missing_content():
    inst = _make_instance(
        partial_call={}, parse_args_fn=lambda: {"files": [{"path": "some/path"}]}
    )
    with pytest.raises(ValueError) as exc:
        inst._update_files()
    assert "Missing content parameter" in str(exc.value)
    assert "{'path': 'some/path'}" in str(exc.value)


def test_update_files_only_adds_allowed_files():
    files = [
        {"path": "p1.txt", "content": "content1"},
        {"path": "p2.txt", "content": "content2"},
        {"path": "p3.txt", "content": "content3"},
    ]

    # allowed_to_edit returns True only for p1.txt and p3.txt
    def allowed(path, content):
        return path in {"p1.txt", "p3.txt"}

    inst = _make_instance(
        partial_call={"name": "write_file"},
        parse_args_fn=lambda: {"files": files},
        allowed_fn=allowed,
    )

    result = inst._update_files()
    assert isinstance(result, set)
    assert result == {"p1.txt", "p3.txt"}
