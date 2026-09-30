# file: aider/commands.py:138-203
# asked: {"lines": [141, 143, 144, 145, 146, 147, 148, 150, 151, 155, 156, 174, 175, 176, 178, 180, 181, 182, 184, 185, 186, 187, 189, 191, 192, 194, 195, 196, 197, 198, 200, 201, 202], "branches": [[174, 175], [174, 191], [175, 176], [175, 178], [181, 182], [181, 184], [185, 186], [185, 189], [186, 185], [186, 187], [194, 195], [194, 197], [197, 198], [197, 200]]}
# gained: {"lines": [141, 143, 144, 145, 146, 147, 148, 150, 151, 155, 156, 174, 175, 176, 178, 180, 181, 182, 184, 185, 186, 187, 189, 191, 192, 194, 195, 196, 197, 198, 200, 201, 202], "branches": [[174, 175], [174, 191], [175, 176], [175, 178], [181, 182], [181, 184], [185, 186], [185, 189], [186, 187], [194, 195], [194, 197], [197, 198], [197, 200]]}

import sys
import types
from types import SimpleNamespace

import pytest


def _make_aider_coders_module(coders_list):
    """
    Create a faux 'aider' package and 'aider.coders' submodule with __all__ set to coders_list.
    coders_list should be a list of objects with 'edit_format' and '__doc__'.
    """
    coders_mod = types.ModuleType("aider.coders")
    coders_mod.__all__ = coders_list
    # also create a top-level 'aider' module that has attribute 'coders'
    aider_mod = types.ModuleType("aider")
    aider_mod.coders = coders_mod
    return aider_mod, coders_mod


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        # store exact message for assertions
        self.outputs.append(msg)

    def tool_error(self, msg):
        self.errors.append(msg)


class DummyMainModel:
    def __init__(self, edit_format):
        self.edit_format = edit_format


class DummyCoderObj:
    def __init__(self, main_model_edit_format=None):
        if main_model_edit_format is not None:
            self.main_model = DummyMainModel(main_model_edit_format)
        else:
            self.main_model = SimpleNamespace(edit_format=None)


@pytest.fixture(autouse=False)
def import_commands():
    """
    Import Commands and SwitchCoder lazily in tests to avoid import-time side effects.
    This fixture returns the Commands class and SwitchCoder exception class from aider.commands.
    """
    # Import inside fixture so tests control module masking of 'aider' before use.
    from aider.commands import Commands, SwitchCoder

    return Commands, SwitchCoder


def _install_fake_aider(monkeypatch, coders_list):
    aider_mod, coders_mod = _make_aider_coders_module(coders_list)
    # Insert into sys.modules so `from aider import coders` works and `import aider.coders` too.
    monkeypatch.setitem(sys.modules, "aider", aider_mod)
    monkeypatch.setitem(sys.modules, "aider.coders", coders_mod)
    return aider_mod, coders_mod


def _make_coder_entry(edit_format, doc=None):
    # Create a tiny object-like coder with edit_format and __doc__
    obj = SimpleNamespace(edit_format=edit_format)
    # __doc__ is a special attribute; setting it on the SimpleNamespace instance works.
    obj.__doc__ = doc
    return obj


def test_cmd_chat_mode_empty_shows_help_and_formats(monkeypatch, import_commands):
    Commands, SwitchCoder = import_commands

    # Prepare fake coders so valid_formats is non-empty
    coder_entries = [
        _make_coder_entry("fmt1", "Formatter One\nMore details"),
        _make_coder_entry("longfmt", "Long Format\nOther"),
    ]
    _install_fake_aider(monkeypatch, coder_entries)

    io = DummyIO()
    # coder used by Commands only needs a main_model.edit_format for other tests; not used here
    coder = DummyCoderObj(main_model_edit_format="fmt1")
    cmd = Commands(io=io, coder=coder)

    # Call with empty args -> should not raise; should call tool_output with header and lists
    ret = cmd.cmd_chat_mode("")
    assert ret is None

    # First output message should indicate available chat modes
    assert any("Chat mode should be one of these" in o for o in io.outputs), io.outputs

    # Should include show_formats like 'help' and 'ask'
    concatenated = "\n".join(io.outputs)
    assert "- help" in concatenated
    assert "- ask" in concatenated

    # Should include our valid edit formats (fmt1 and longfmt) in the listing
    assert "fmt1" in concatenated
    assert "longfmt" in concatenated


def test_cmd_chat_mode_invalid_nonempty_uses_tool_error(monkeypatch, import_commands):
    Commands, SwitchCoder = import_commands

    coder_entries = [
        _make_coder_entry("alpha", "Alpha coder"),
    ]
    _install_fake_aider(monkeypatch, coder_entries)

    io = DummyIO()
    coder = DummyCoderObj(main_model_edit_format="alpha")
    cmd = Commands(io=io, coder=coder)

    # Non-empty but invalid chat mode -> should call tool_error and then tool_output listings
    bad = "no_such_mode"
    ret = cmd.cmd_chat_mode(bad)
    # Function returns None after printing listings
    assert ret is None

    # tool_error should have been called with message including the bad mode
    assert any(bad in e and "should be one of these" in e for e in io.errors), io.errors

    # For non-empty invalid ef, the header is sent to tool_error; outputs should still contain the formats list
    assert any("- help" in o or "- ask" in o for o in io.outputs), io.outputs
    combined = "\n".join(io.outputs)
    assert "- alpha" in combined


def test_cmd_chat_mode_switchcoder_branches(monkeypatch, import_commands):
    Commands, SwitchCoder = import_commands

    # Prepare valid coder formats used for testing:
    coder_entries = [
        _make_coder_entry("myformat", "My Format"),
        _make_coder_entry("another", "Another Format"),
    ]
    _install_fake_aider(monkeypatch, coder_entries)

    # 1) When ef is a valid edit_format (myformat) -> SwitchCoder with summarize_from_coder True
    io1 = DummyIO()
    coder1 = DummyCoderObj(main_model_edit_format="unused")
    cmd1 = Commands(io=io1, coder=coder1)
    with pytest.raises(SwitchCoder) as excinfo1:
        cmd1.cmd_chat_mode("myformat")
    exc1 = excinfo1.value
    # SwitchCoder stores its values in .kwargs
    assert exc1.kwargs.get("edit_format") == "myformat"
    assert exc1.kwargs.get("summarize_from_coder") is True

    # 2) When ef == 'code' -> use coder.main_model.edit_format and summarize_from_coder False
    io2 = DummyIO()
    coder2 = DummyCoderObj(main_model_edit_format="myformat_from_main")
    cmd2 = Commands(io=io2, coder=coder2)
    with pytest.raises(SwitchCoder) as excinfo2:
        cmd2.cmd_chat_mode("code")
    exc2 = excinfo2.value
    assert exc2.kwargs.get("edit_format") == "myformat_from_main"
    assert exc2.kwargs.get("summarize_from_coder") is False

    # 3) When ef == 'ask' -> edit_format should be 'ask' and summarize_from_coder False
    io3 = DummyIO()
    coder3 = DummyCoderObj(main_model_edit_format="does_not_matter")
    cmd3 = Commands(io=io3, coder=coder3)
    with pytest.raises(SwitchCoder) as excinfo3:
        cmd3.cmd_chat_mode("ask")
    exc3 = excinfo3.value
    assert exc3.kwargs.get("edit_format") == "ask"
    assert exc3.kwargs.get("summarize_from_coder") is False
