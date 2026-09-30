import pytest
from types import SimpleNamespace
import openhands.events.action.files as files
from openhands.events.event import FileEditSource


def test_repr_llm_based_round_077():
    # LLM-based edit should include range and content blocks
    obj = SimpleNamespace(
        path="some/path.txt",
        thought="make changes",
        impl_source=FileEditSource.LLM_BASED_EDIT,
        start=10,
        end=20,
        content="line1\nline2"
    )

    out = files.FileEditAction.__repr__(obj)

    assert "**FileEditAction**" in out
    assert "Path: [some/path.txt]" in out
    assert "Thought: make changes" in out
    # Range formatting
    assert "Range: [L10:L20]" in out
    # Content block formatting and content preserved
    assert "Content:\n```" in out
    assert "line1\nline2" in out
    assert out.strip().endswith("```"), "expected closing code fence"


def test_repr_create_round_077():
    # OH_ACI (non-LLM) with 'create' command shows created file text
    obj = SimpleNamespace(
        path="new/file.py",
        thought="create file",
        impl_source=object(),  # anything not equal to LLM_BASED_EDIT
        command="create",
        file_text="print(\"hello\")"
    )

    out = files.FileEditAction.__repr__(obj)

    assert "Command: create" in out
    assert "Created File with Text:" in out
    assert "print(\"hello\")" in out


def test_repr_str_replace_round_077():
    # str_replace should include old and new string blocks
    obj = SimpleNamespace(
        path="replace/me.txt",
        thought="replace strings",
        impl_source=None,
        command="str_replace",
        old_str="old_value",
        new_str="new_value"
    )

    out = files.FileEditAction.__repr__(obj)

    assert "Command: str_replace" in out
    assert "Old String: ```" in out
    assert "old_value" in out
    assert "New String: ```" in out
    assert "new_value" in out


def test_repr_insert_round_077():
    # insert command shows insert line and new string
    obj = SimpleNamespace(
        path="insert/here.txt",
        thought="insert line",
        impl_source=object(),
        command="insert",
        insert_line=42,
        new_str="inserted line"
    )

    out = files.FileEditAction.__repr__(obj)

    assert "Command: insert" in out
    assert "Insert Line: 42" in out
    assert "New String: ```" in out
    assert "inserted line" in out


def test_repr_undo_edit_round_077():
    # undo_edit should output the Undo Edit line
    obj = SimpleNamespace(
        path="undo/it.txt",
        thought="undo",
        impl_source=object(),
        command="undo_edit"
    )

    out = files.FileEditAction.__repr__(obj)

    assert "Command: undo_edit" in out
    assert "Undo Edit" in out
