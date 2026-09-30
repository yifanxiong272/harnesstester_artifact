import builtins
import types
import pytest

from aider.io import InputOutput


class _Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        # record a shallow representation of the call
        self.calls.append((args, kwargs))


class FakePromptSession:
    def __init__(self, return_value):
        self.return_value = return_value
        self.recorded = []

    def prompt(self, prompt, default=None, style=None, complete_while_typing=None):
        # Record the received arguments for assertion and return the predetermined value
        self.recorded.append({
            "prompt": prompt,
            "default": default,
            "style": style,
            "complete_while_typing": complete_while_typing,
        })
        return self.return_value


def _make_io_instance():
    # Create an InputOutput instance without calling __init__ to avoid heavy dependencies
    inst = object.__new__(InputOutput)
    # Minimal attributes used by prompt_ask
    inst.num_user_asks = 0
    inst.yes = None
    inst.prompt_session = None
    # restore_multiline wrapper expects this attribute to exist
    inst.multiline_mode = False
    inst._get_style = lambda: "FAKE_STYLE"
    inst.ring_bell = lambda: None
    # append_chat_history signature: (text, linebreak=True, blockquote=True, strip=None)
    inst.append_chat_history = lambda text, linebreak=True, blockquote=True, strip=None: setattr(inst, "_last_history", (text, linebreak, blockquote))

    # tool_output and other outputs will be replaced in tests with recorders
    inst.tool_output = lambda *a, **k: None
    return inst


def test_prompt_session_with_subject_round_144():
    io = _make_io_instance()
    # Prepare a recorder for tool_output calls
    recorder = _Recorder()
    io.tool_output = recorder

    # Provide a fake prompt session that returns a predictable response
    io.prompt_session = FakePromptSession("user response")

    # Ensure yes is None so we exercise the prompt path
    io.yes = None

    res = io.prompt_ask("Q?", default="D", subject="SUBJECT")

    # The prompt_session's prompt should have been invoked and returned its value
    assert res == "user response"

    # Subject handling should call tool_output twice: a blank/tool header call, then subject bold call
    assert len(recorder.calls) >= 2
    first_args, first_kwargs = recorder.calls[0]
    second_args, second_kwargs = recorder.calls[1]

    # first call is invoked with no positional arguments
    assert first_args == ()
    # second call should contain the subject as first positional argument and bold=True in kwargs
    assert second_args == ("SUBJECT",)
    assert second_kwargs.get("bold") is True

    # append_chat_history should have been called and recorded on the instance
    assert hasattr(io, "_last_history")
    hist_text, linebreak, blockquote = io._last_history
    # The history should be '<question stripped> <response stripped>'
    assert hist_text == "Q? user response"
    assert linebreak is True and blockquote is True


def test_yes_true_with_subject_triggers_tool_output_hist_round_144():
    io = _make_io_instance()
    recorder = _Recorder()
    io.tool_output = recorder

    # With yes True, prompt_ask should short-circuit and return 'yes'
    io.yes = True

    res = io.prompt_ask("Are you sure?", default="nope", subject="S")

    assert res == "yes"

    # Expect: two calls from subject handling, plus one call for the history because yes is True
    # Total calls should be at least 3
    assert len(recorder.calls) >= 3

    # Validate the first two calls correspond to subject handling
    assert recorder.calls[0][0] == ()
    assert recorder.calls[1][0] == ("S",)
    assert recorder.calls[1][1].get("bold") is True

    # The last recorded tool_output call should contain the history string
    last_args, last_kwargs = recorder.calls[-1]
    # history built as '<question.strip()> <res.strip()>'
    assert last_args[0] == "Are you sure? yes"

    # append_chat_history recorded on the instance
    assert hasattr(io, "_last_history")
    hist_text, linebreak, blockquote = io._last_history
    assert hist_text == "Are you sure? yes"
    assert linebreak is True and blockquote is True


def test_input_eof_uses_default_round_144(monkeypatch):
    io = _make_io_instance()
    recorder = _Recorder()
    io.tool_output = recorder

    # No prompt session -> branch that calls builtins.input
    io.prompt_session = None
    io.yes = None

    # Patch builtins.input to raise EOFError to exercise the EOFError handler
    def _raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", _raise_eof)

    res = io.prompt_ask("Enter something?", default="DEFAULT")

    # Should return the default when EOFError is raised
    assert res == "DEFAULT"

    # append_chat_history should have been called with the default value
    assert hasattr(io, "_last_history")
    hist_text, linebreak, blockquote = io._last_history
    assert hist_text == "Enter something? DEFAULT"
    assert linebreak is True and blockquote is True

    # When yes is None, no additional tool_output(hist) should have been invoked
    # The subject wasn't provided so recorder.calls should be empty
    assert recorder.calls == []
