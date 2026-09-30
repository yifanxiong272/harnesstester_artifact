import types
from types import SimpleNamespace
import pytest

from aider import commands
from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        self.outputs.append(msg)

    def tool_error(self, msg):
        self.errors.append(msg)


class DummyCoder:
    def __init__(self, chunks):
        self._chunks = chunks

    def format_chat_chunks(self):
        return self._chunks


def make_chunks():
    # repo: a user message with simple string content
    repo = [{"role": "user", "content": "repo user text"}]

    # readonly_files: contains a non-user message that should be skipped
    readonly_files = [{"role": "system", "content": "should be skipped"}]

    # chat_files: a user message whose content is a multipart list
    chat_files = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "part text 1"},
                {"type": "image", "text": "image ignored"},
                {"type": "text", "text": "part text 2"},
            ],
        }
    ]

    return SimpleNamespace(repo=repo, readonly_files=readonly_files, chat_files=chat_files)


def make_self(io=None, coder=None):
    io = io or DummyIO()
    coder = coder or DummyCoder(make_chunks())
    return SimpleNamespace(io=io, coder=coder)


def test_cmd_copy_context_success_round_037(monkeypatch):
    """pyperclip.copy succeeds -> content passed and success output called"""
    captured = {}

    def fake_copy(text):
        # capture the text that would be copied
        captured['text'] = text

    # Patch the symbol in the module where the function resolves it
    monkeypatch.setattr(commands, "pyperclip", SimpleNamespace(copy=fake_copy, PyperclipException=Exception))

    io = DummyIO()
    self = make_self(io=io)

    # Call the underlying function (unbound) with our lightweight self
    Commands.cmd_copy_context(self, args="--flag value")

    assert 'text' in captured, "pyperclip.copy was not called"
    copied = captured['text']

    # Expect repo user text to appear
    assert "repo user text" in copied

    # Expect multipart text parts to be concatenated and image ignored
    assert "part text 1" in copied
    assert "part text 2" in copied
    assert "image ignored" not in copied

    # args should be included in the appended instruction block
    assert "--flag value" in copied

    # Ensure the success output was emitted
    assert any("Copied code context to clipboard." in o for o in io.outputs)
    assert io.errors == []


def test_cmd_copy_context_pyperclip_exception_round_037(monkeypatch):
    """pyperclip.PyperclipException -> tool_error + install hint output"""

    class FakePyperclipExc(Exception):
        pass

    def fake_copy_raise(text):
        raise FakePyperclipExc("no clipboard")

    monkeypatch.setattr(commands, "pyperclip", SimpleNamespace(copy=fake_copy_raise, PyperclipException=FakePyperclipExc))

    io = DummyIO()
    self = make_self(io=io)

    Commands.cmd_copy_context(self, args=None)

    # tool_error should have been called with the failure message
    assert any("Failed to copy to clipboard" in e for e in io.errors)

    # tool_output should include the install hint
    assert any("You may need to install xclip or xsel on Linux, or pbcopy on macOS." in o for o in io.outputs)


def test_cmd_copy_context_generic_exception_round_037(monkeypatch):
    """generic Exception from pyperclip.copy -> unexpected error branch"""

    def fake_copy_raise(text):
        raise RuntimeError("boom")

    # Use a pyperclip object that will raise a generic Exception from copy
    monkeypatch.setattr(commands, "pyperclip", SimpleNamespace(copy=fake_copy_raise, PyperclipException=RuntimeError))

    io = DummyIO()
    self = make_self(io=io)

    Commands.cmd_copy_context(self, args="")

    # Should have an unexpected error message
    assert any("An unexpected error occurred while copying to clipboard:" in e for e in io.errors)

    # In the generic-exception branch, the install hint should NOT be printed
    assert not any("You may need to install xclip" in o for o in io.outputs)
