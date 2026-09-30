import pytest

from pr_agent.tools import pr_help_docs as phd


class DummyLogger:
    def __init__(self):
        self.error_calls = []
        self.warning_calls = []
        self.exception_calls = []

    def error(self, msg):
        self.error_calls.append(msg)

    def warning(self, msg):
        self.warning_calls.append(msg)

    def exception(self, msg):
        self.exception_calls.append(msg)


def test_aggregate_empty_file_contents_round_109(monkeypatch):
    logger = DummyLogger()
    # patch get_logger to return our dummy
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    inp = {"README.md": "   \n\t"}
    result = phd.aggregate_documentation_files_for_prompt_contents(inp, return_just_headings=False)

    # empty contents should be skipped and final result empty
    assert result == ""
    assert len(logger.error_calls) == 1
    assert "Got empty file contents for: README.md. Skipping this file." in logger.error_calls[0]


def test_aggregate_return_just_headings_with_headings_round_109(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # make return_document_headings produce headings text
    monkeypatch.setattr(phd, "return_document_headings", lambda text, ext: "H1\nH2")

    inp = {"guide.md": "  some text  "}
    result = phd.aggregate_documentation_files_for_prompt_contents(inp, return_just_headings=True)

    expected = (
        "\n==file name==\n\nguide.md\n\n==index==\n\n0\n\n==file headings==\n\n"
        "H1\nH2\n=========\n\n"
    )
    assert result == expected
    # no warnings or errors expected
    assert logger.warning_calls == []
    assert logger.error_calls == []


def test_aggregate_return_just_headings_without_headings_round_109(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    # simulate no headings returned
    monkeypatch.setattr(phd, "return_document_headings", lambda text, ext: "")

    inp = {"file.txt": "content"}
    result = phd.aggregate_documentation_files_for_prompt_contents(inp, return_just_headings=True)

    expected = (
        "\n==file name==\n\nfile.txt\n\n==index==\n\n0\n\n"
    )
    assert result == expected
    assert len(logger.warning_calls) == 1
    assert "No headers for: file.txt. Will only use filename" in logger.warning_calls[0]


def test_aggregate_full_content_round_109(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    inp = {"notes.md": "  Hello world  \n"}
    result = phd.aggregate_documentation_files_for_prompt_contents(inp, return_just_headings=False)

    expected = (
        "\n==file name==\n\nnotes.md\n\n==file content==\n\nHello world\n=========\n\n"
    )
    assert result == expected
    assert logger.error_calls == []
    assert logger.warning_calls == []


def test_exception_handling_round_109(monkeypatch):
    # If any inner call raises, the function should catch and return empty string and log an exception
    logger = DummyLogger()
    monkeypatch.setattr(phd, "get_logger", lambda: logger)

    def raising_return_headings(text, ext):
        raise RuntimeError("boom")

    monkeypatch.setattr(phd, "return_document_headings", raising_return_headings)

    inp = {"a.md": "some content"}
    result = phd.aggregate_documentation_files_for_prompt_contents(inp, return_just_headings=True)

    assert result == ""
    assert len(logger.exception_calls) == 1
    assert "Unexpected exception thrown. Returning empty result." in logger.exception_calls[0]
