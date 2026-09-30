# file: pr_agent/tools/pr_help_docs.py:81-117
# asked: {"lines": [82, 83, 84, 86, 87, 88, 90, 92, 93, 96, 99, 100, 101, 102, 103, 106, 108, 109, 111, 112, 114, 115, 116, 117], "branches": [[86, 87], [86, 90], [90, 92], [90, 93], [93, 96], [93, 111], [100, 101], [100, 106], [102, 100], [102, 103], [106, 108], [106, 114], [108, 106], [108, 109]]}
# gained: {"lines": [82, 83, 84, 86, 87, 88, 90, 92, 93, 96, 99, 100, 101, 102, 103, 106, 108, 109, 111, 112, 114, 115, 116, 117], "branches": [[86, 87], [86, 90], [90, 92], [90, 93], [93, 96], [93, 111], [100, 101], [100, 106], [102, 100], [102, 103], [106, 108], [106, 114], [108, 109]]}

import pytest

from pr_agent.tools import pr_help_docs as phd


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.exceptions = []

    def error(self, *args, **kwargs):
        # record a simple joined string for easy assertions
        self.errors.append(" ".join(str(a) for a in args))

    def exception(self, *args, **kwargs):
        self.exceptions.append(" ".join(str(a) for a in args))


def test_markdown_headings_extracted():
    text = "Intro line\n  # Heading One  \nSome text\n## Heading Two\n#HeadingThree\n\n"
    res = phd.return_document_headings(text, ".md")
    # result is newline-joined set, so order is not guaranteed
    parts = set(res.split("\n")) if res else set()
    expected = {"# Heading One", "## Heading Two", "#HeadingThree"}
    assert parts == expected


def test_empty_or_non_text_logs_and_returns_empty(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # empty text should trigger the early error path
    res_empty = phd.return_document_headings("", ".md")
    assert res_empty == ""
    assert any("Empty or non text content" in e for e in logger.errors)

    # non-text (no letters) should also trigger same path
    logger.errors.clear()
    res_nontext = phd.return_document_headings("1234 4567 !!!", ".md")
    assert res_nontext == ""
    assert any("Empty or non text content" in e for e in logger.errors)


def test_unsupported_extension_logs_and_returns_empty(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # text contains letters so it bypasses the empty check, but extension is unsupported
    res = phd.return_document_headings("This has letters", ".txt")
    assert res == ""
    # should have logged about unsupported extension
    assert any("Unsupported file extension" in e for e in logger.errors)


def test_restructuredtext_headings_extracted(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # Create two headings that meet the rule: heading length <= marker length
    # 'Shrt' length 4 with '----' marker length 4
    # 'X' length 1 with '^^^^' marker length 4
    text = "Shrt\n----\nOther line\nX\n^^^^\n"
    res = phd.return_document_headings(text, ".rst")
    parts = set(res.split("\n")) if res else set()
    expected = {"Shrt", "X"}
    assert parts == expected
    # No errors should be logged for this valid rst extraction
    assert not logger.errors


def test_exception_in_search_is_caught_and_logged(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # Make re.search raise to force the broad exception handler
    def raise_search(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(phd.re, "search", raise_search)

    res = phd.return_document_headings("Some text", ".md")
    assert res == ""
    # exception handler should have been invoked
    assert any("Unexpected exception thrown" in e or "Unexpected exception" in e for e in logger.exceptions)
