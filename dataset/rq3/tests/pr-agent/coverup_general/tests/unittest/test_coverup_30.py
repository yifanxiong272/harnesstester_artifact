# file: pr_agent/tools/pr_help_docs.py:81-117
# asked: {"lines": [82, 83, 84, 86, 87, 88, 90, 92, 93, 96, 99, 100, 101, 102, 103, 106, 108, 109, 111, 112, 114, 115, 116, 117], "branches": [[86, 87], [86, 90], [90, 92], [90, 93], [93, 96], [93, 111], [100, 101], [100, 106], [102, 100], [102, 103], [106, 108], [106, 114], [108, 106], [108, 109]]}
# gained: {"lines": [82, 83, 84, 86, 87, 88, 90, 92, 93, 96, 99, 100, 101, 102, 103, 106, 108, 109, 111, 112, 114, 115, 116, 117], "branches": [[86, 87], [86, 90], [90, 92], [90, 93], [93, 96], [93, 111], [100, 101], [100, 106], [102, 100], [102, 103], [106, 108], [106, 114], [108, 109]]}

import pytest

from pr_agent.tools.pr_help_docs import return_document_headings


class FakeLogger:
    def __init__(self):
        self.errors = []
        self.exceptions = []

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def test_md_headings_and_no_logs(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    text = "# Heading1\nSome text\n## Heading2\nAnother line\n"
    result = return_document_headings(text, ".md")

    result_set = set(result.split("\n")) if result else set()
    assert result_set == {"# Heading1", "## Heading2"}
    assert fake_logger.errors == []
    assert fake_logger.exceptions == []


def test_rst_headings_and_no_logs(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    # Two section headings with underline markers. Make sure underline lengths are >= heading length.
    # "Title Two" length is 9 characters, so use 9 '=' characters.
    text = "Title One\n---------\nSome body\nTitle Two\n=========\n"
    result = return_document_headings(text, ".rst")

    result_set = set(result.split("\n")) if result else set()
    assert result_set == {"Title One", "Title Two"}
    assert fake_logger.errors == []
    assert fake_logger.exceptions == []


def test_unsupported_extension_logs_and_returns_empty(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    text = "Hello World"
    result = return_document_headings(text, ".txt")
    assert result == ""
    # Ensure the error about unsupported extension was logged
    assert any("Unsupported file extension: .txt" in msg for msg in fake_logger.errors)


def test_empty_or_non_text_logs_and_returns_empty(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    # Text contains no alphabetic characters -> treated as non-text content
    text = "1234567890"
    result = return_document_headings(text, ".md")
    assert result == ""
    assert any("Empty or non text content found in text" in msg for msg in fake_logger.errors)


def test_exception_block_logs_and_returns_empty(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    class Bad:
        def split(self, _sep):
            raise ValueError("split failed")

        def __str__(self):
            return "<Bad>"

    result = return_document_headings(Bad(), ".md")
    assert result == ""
    # Ensure exception logging was invoked
    assert any("Unexpected exception thrown. Returning empty result." in msg for msg in fake_logger.exceptions)
