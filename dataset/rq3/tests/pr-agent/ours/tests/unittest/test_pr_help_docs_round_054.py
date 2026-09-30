import pytest

from pr_agent.tools import pr_help_docs as ph
from pr_agent.tools.pr_help_docs import return_document_headings


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.exceptions = []

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def test_md_headings_round_054(monkeypatch):
    logger = DummyLogger()
    # patch the logger used inside the module under test
    monkeypatch.setattr(ph, 'get_logger', lambda: logger)

    text = (
        "Intro\n"
        "# Heading 1\n"
        "Some text\n"
        "   ## Subheading 2\n"
        "Not a heading\n"
        "#Heading3\n"
    )

    out = return_document_headings(text, '.md')
    # The implementation returns a newline-joined set, order is not guaranteed.
    out_set = set(out.split('\n')) if out else set()

    expected = {"# Heading 1", "## Subheading 2", "#Heading3"}
    assert out_set == expected
    # ensure no error/exception was logged
    assert logger.errors == []
    assert logger.exceptions == []


def test_rst_headings_underline_round_054(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, 'get_logger', lambda: logger)

    # Create RST-like content: heading line followed by a marker line of same char
    text = (
        "First\n"
        "=====\n"
        "\n"
        "Second\n"
        "------\n"
        "\n"
        "Third\n"
        "......\n"
    )

    out = return_document_headings(text, '.rst')
    out_set = set(out.split('\n')) if out else set()
    expected = {"First", "Second", "Third"}
    assert out_set == expected
    assert logger.errors == []
    assert logger.exceptions == []


def test_unsupported_extension_round_054(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, 'get_logger', lambda: logger)

    text = "Some regular text with letters"
    out = return_document_headings(text, '.txt')
    # unsupported extension should return empty string and log an error
    assert out == ""
    assert len(logger.errors) == 1
    assert "Unsupported file extension" in logger.errors[0]
    assert logger.exceptions == []


def test_empty_or_nontxt_content_round_054(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, 'get_logger', lambda: logger)

    # text contains no alphabetic characters => treated as non-text
    text = "1234567890"
    out = return_document_headings(text, '.md')
    assert out == ""
    # should log an error with the provided text
    assert len(logger.errors) == 1
    assert "Empty or non text content found in text" in logger.errors[0]
    assert logger.exceptions == []


def test_exception_is_caught_round_054(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, 'get_logger', lambda: logger)

    # Pass an object that does not implement split -> will raise AttributeError
    bad_text = object()
    out = return_document_headings(bad_text, '.md')
    assert out == ""
    # should have captured the exception via logger.exception
    assert len(logger.exceptions) == 1
    assert "Unexpected exception thrown" in logger.exceptions[0] or logger.exceptions[0] == "Unexpected exception thrown. Returning empty result."
