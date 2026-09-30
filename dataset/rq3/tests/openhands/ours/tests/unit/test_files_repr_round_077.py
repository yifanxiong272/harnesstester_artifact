import pytest

from openhands.events.action.files import FileEditAction
from openhands.events.event import FileEditSource


def test_llm_based_repr_round_077():
    # LLM-based edit should include Range and Content blocks
    a = FileEditAction(
        path="some/path",
        content="abc",
        start=2,
        end=5,
        thought="note",
        impl_source=FileEditSource.LLM_BASED_EDIT,
    )

    got = repr(a)
    expected = "**FileEditAction**\n"
    expected += "Path: [some/path]\n"
    expected += "Thought: note\n"
    expected += "Range: [L2:L5]\n"
    expected += "Content:\n```\nabc\n```\n"

    assert got == expected


def test_create_command_repr_round_077():
    # OH_ACI create command should include Command and Created File with Text block
    a = FileEditAction(
        path="p/c",
        command="create",
        file_text="hello world",
        thought="created",
        impl_source=FileEditSource.OH_ACI,
    )

    got = repr(a)
    expected = "**FileEditAction**\n"
    expected += "Path: [p/c]\n"
    expected += "Thought: created\n"
    expected += "Command: create\n"
    expected += "Created File with Text:\n```\nhello world\n```\n"

    assert got == expected


def test_str_replace_command_repr_round_077():
    # OH_ACI str_replace command should include Old String and New String blocks
    a = FileEditAction(
        path="x",
        command="str_replace",
        old_str="old",
        new_str="new",
        thought="replace",
        impl_source=FileEditSource.OH_ACI,
    )

    got = repr(a)
    expected = "**FileEditAction**\n"
    expected += "Path: [x]\n"
    expected += "Thought: replace\n"
    expected += "Command: str_replace\n"
    expected += "Old String: ```\nold\n```\n"
    expected += "New String: ```\nnew\n```\n"

    assert got == expected


def test_insert_command_repr_round_077():
    # OH_ACI insert command should include Insert Line and New String block
    a = FileEditAction(
        path="file.txt",
        command="insert",
        insert_line=10,
        new_str="inserted line",
        thought="inserting",
        impl_source=FileEditSource.OH_ACI,
    )

    got = repr(a)
    expected = "**FileEditAction**\n"
    expected += "Path: [file.txt]\n"
    expected += "Thought: inserting\n"
    expected += "Command: insert\n"
    expected += "Insert Line: 10\n"
    expected += "New String: ```\ninserted line\n```\n"

    assert got == expected


def test_undo_edit_command_repr_round_077():
    # OH_ACI undo_edit command should include the Undo Edit line
    a = FileEditAction(
        path="u",
        command="undo_edit",
        thought="undoing",
        impl_source=FileEditSource.OH_ACI,
    )

    got = repr(a)
    expected = "**FileEditAction**\n"
    expected += "Path: [u]\n"
    expected += "Thought: undoing\n"
    expected += "Command: undo_edit\n"
    expected += "Undo Edit\n"

    assert got == expected
