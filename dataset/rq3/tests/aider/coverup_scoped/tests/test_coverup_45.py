# file: aider/io.py:1023-1041
# asked: {"lines": [1024, 1025, 1026, 1028, 1031, 1032, 1034, 1035, 1036, 1039, 1041], "branches": [[1024, 1025], [1024, 1028], [1031, 1032], [1031, 1034], [1034, 1035], [1034, 1039]]}
# gained: {"lines": [1024, 1025, 1026, 1028, 1031, 1032, 1034, 1035, 1036, 1039, 1041], "branches": [[1024, 1025], [1024, 1028], [1031, 1032], [1031, 1034], [1034, 1035], [1034, 1039]]}

import types
import pytest

import aider.io as aio
from aider.io import InputOutput


class FakeConsole:
    def __init__(self):
        self.called = False
        self.last = None

    def print(self, obj):
        self.called = True
        self.last = obj


class FakeMarkdown:
    def __init__(self, text, style=None, code_theme=None):
        self.text = text
        self.style = style
        self.code_theme = code_theme


class FakeText:
    def __init__(self, text):
        self.text = text


def _bind_assistant_output_to(dummy):
    # Bind the unbound function to our dummy instance
    return types.MethodType(InputOutput.assistant_output, dummy)


def test_assistant_output_empty_message_calls_tool_warning_and_does_not_print(monkeypatch):
    dummy = type("D", (), {})()
    console = FakeConsole()
    dummy.console = console

    warned = {}

    def fake_tool_warning(msg):
        warned['msg'] = msg

    dummy.tool_warning = fake_tool_warning

    # Bind method and call with empty message
    meth = _bind_assistant_output_to(dummy)
    # empty string should trigger the "if not message" branch
    result = meth("")
    assert result is None
    assert 'msg' in warned
    assert "Empty response received from LLM" in warned['msg']
    assert console.called is False


def test_assistant_output_pretty_none_uses_self_pretty_and_prints_markdown(monkeypatch):
    # Replace the module Markdown with FakeMarkdown to capture constructor args
    monkeypatch.setattr(aio, "Markdown", FakeMarkdown, raising=False)
    monkeypatch.setattr(aio, "Text", FakeText, raising=False)

    dummy = type("D", (), {})()
    console = FakeConsole()
    dummy.console = console
    # set attributes used by assistant_output
    dummy.pretty = True
    dummy.assistant_output_color = "the-color"
    dummy.code_theme = "the-theme"

    # tool_warning should not be called here; provide one just in case
    dummy.tool_warning = lambda msg: (_ for _ in ()).throw(RuntimeError("tool_warning should not be called"))

    meth = _bind_assistant_output_to(dummy)
    message = "some **markdown** content"
    meth(message, pretty=None)  # pretty None -> uses self.pretty which is True

    assert console.called is True
    # The printed object should be our FakeMarkdown with captured args
    assert isinstance(console.last, FakeMarkdown)
    assert console.last.text == message
    assert console.last.style == dummy.assistant_output_color
    assert console.last.code_theme == dummy.code_theme


def test_assistant_output_pretty_false_uses_text_and_prints_text_instance(monkeypatch):
    # Replace the module Text with FakeText to capture constructor args
    monkeypatch.setattr(aio, "Markdown", FakeMarkdown, raising=False)
    monkeypatch.setattr(aio, "Text", FakeText, raising=False)

    dummy = type("D", (), {})()
    console = FakeConsole()
    dummy.console = console
    # set attributes used by assistant_output
    dummy.pretty = True  # should be overridden by explicit pretty=False
    dummy.assistant_output_color = "unused"
    dummy.code_theme = "unused"

    dummy.tool_warning = lambda msg: (_ for _ in ()).throw(RuntimeError("tool_warning should not be called"))

    meth = _bind_assistant_output_to(dummy)
    message = "plain text response"
    meth(message, pretty=False)  # explicit False should force Text path

    assert console.called is True
    assert isinstance(console.last, FakeText)
    assert console.last.text == message
