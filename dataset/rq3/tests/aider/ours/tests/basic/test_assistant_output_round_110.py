import pytest


def _make_fake_console():
    class Console:
        def __init__(self):
            self.last = None

        def print(self, obj):
            # record the last printed object
            self.last = obj

    return Console()


def test_assistant_output_empty_message_round_110():
    """When message is falsy, tool_warning must be called and nothing printed."""
    from aider.io import InputOutput

    warnings = []

    def tool_warning(msg):
        warnings.append(msg)

    fake = type("FakeSelf", (), {})()
    # minimal attributes used by assistant_output for this branch
    fake.tool_warning = tool_warning
    fake.console = _make_fake_console()
    # ensure pretty value exists but is irrelevant for empty message path
    fake.pretty = True
    fake.assistant_output_color = "acol"
    fake.code_theme = "ctheme"

    # Call with empty string (falsy). Should trigger tool_warning and return None.
    result = InputOutput.assistant_output(fake, "")

    assert result is None
    assert warnings == [
        "Empty response received from LLM. Check your provider account?"
    ], "Expected the explicit tool_warning message for empty LLM responses"


def test_assistant_output_pretty_true_round_110(monkeypatch):
    """When pretty is None and self.pretty is True, Markdown is constructed with
    style and code_theme and printed via console.print.
    """
    from aider import io
    from aider.io import InputOutput

    md_calls = []

    def fake_markdown(message, style=None, code_theme=None):
        # capture call details and return an identifiable sentinel
        md_calls.append((message, style, code_theme))
        return {"_kind": "Markdown", "message": message, "style": style, "code_theme": code_theme}

    monkeypatch.setattr(io, "Markdown", fake_markdown)

    fake = type("FakeSelf", (), {})()
    fake.pretty = True  # will be used when pretty is None
    fake.assistant_output_color = "assistant-color"
    fake.code_theme = "monokai"
    fake.console = _make_fake_console()

    # Pass pretty=None to exercise the branch that sets pretty = self.pretty
    InputOutput.assistant_output(fake, "# heading", pretty=None)

    assert md_calls == [("# heading", "assistant-color", "monokai")]
    # console.print should receive the object returned by our fake_markdown
    assert fake.console.last == {
        "_kind": "Markdown",
        "message": "# heading",
        "style": "assistant-color",
        "code_theme": "monokai",
    }


def test_assistant_output_pretty_false_round_110(monkeypatch):
    """When pretty is False, Text(...) is constructed and printed. Ensure the
    message flows through Text and to console.print unchanged.
    """
    from aider import io
    from aider.io import InputOutput

    text_calls = []

    def fake_text(message):
        text_calls.append(message)
        return ("TextSentinel", message)

    monkeypatch.setattr(io, "Text", fake_text)

    fake = type("FakeSelf", (), {})()
    # even if self.pretty is True, explicit pretty=False should take precedence
    fake.pretty = True
    fake.assistant_output_color = "assistant-color"
    fake.code_theme = "monokai"
    fake.console = _make_fake_console()

    InputOutput.assistant_output(fake, "plain text content", pretty=False)

    assert text_calls == ["plain text content"]
    assert fake.console.last == ("TextSentinel", "plain text content")
