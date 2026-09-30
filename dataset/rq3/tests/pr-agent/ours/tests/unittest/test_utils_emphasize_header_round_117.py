import pr_agent.algo.utils as utils
from pr_agent.algo.utils import emphasize_header
import pytest


def test_no_colon_round_117():
    """If the input has no ': ', the original string is returned unchanged."""
    s = "This string has no colon separator"
    out = emphasize_header(s)
    assert out == s


def test_only_markdown_with_link_round_117():
    """When only_markdown is True and a reference_link is provided, the header
    (up to and including the colon) is wrapped as a bold markdown link and
    followed by a newline and the remainder (including the leading space).
    """
    s = "Title: rest of the line"
    out = emphasize_header(s, only_markdown=True, reference_link="http://example.com")
    # Expect [**Title:**](http://example.com)\n + the remainder starting with the space
    assert out == "[**Title:**](http://example.com)\n rest of the line"


def test_only_markdown_without_link_round_117():
    """When only_markdown is True and no link is provided, header is bolded
    and followed by newline + remainder (with leading space preserved).
    """
    s = "Header: more"
    out = emphasize_header(s, only_markdown=True, reference_link=None)
    assert out == "**Header:**\n more"


def test_html_with_link_round_117():
    """When only_markdown is False and a reference_link is provided, the
    header is wrapped in <strong><a href='...'>...</a></strong><br> and the
    remainder (including the leading space) is appended.
    """
    s = "Note: additional"
    out = emphasize_header(s, only_markdown=False, reference_link="https://a.b")
    assert out == "<strong><a href='https://a.b'>Note:</a></strong><br> additional"


def test_html_without_link_round_117():
    """When only_markdown is False and no link is provided, the header is
    wrapped in <strong>...</strong><br> and the remainder appended.
    """
    s = "Lead: follow"
    out = emphasize_header(s, only_markdown=False, reference_link=None)
    assert out == "<strong>Lead:</strong><br> follow"


def test_exception_round_117(monkeypatch):
    """Trigger an exception inside the function (by passing a non-str) and
    assert that the exception branch is used: the module's logger.exception is
    called and the original (invalid) input is returned unchanged.
    """
    class DummyLogger:
        def __init__(self):
            self.called = False
            self.last_msg = None

        def exception(self, msg):
            self.called = True
            self.last_msg = msg

    dummy = DummyLogger()
    # Patch the symbol where emphasize_header resolves get_logger
    monkeypatch.setattr(utils, "get_logger", lambda: dummy)

    # Pass a value that will raise inside the try (None has no .find)
    value = None
    result = emphasize_header(value)

    # Function should return the original input on exception
    assert result is value
    # And the patched logger should have been used to record the exception
    assert dummy.called is True
    assert isinstance(dummy.last_msg, str)
    assert "Failed to emphasize header" in dummy.last_msg
