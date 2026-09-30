import pytest

from pr_agent.tools.pr_help_docs import format_markdown_q_and_a_response


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def test_format_markdown_q_and_a_response_normal_round_087(monkeypatch):
    """
    Normal flow: two relevant sections, one with a header and one without.
    Ensures base_url_prefix is sanitized and format_markdown_header output is used.
    """
    fake_logger = FakeLogger()

    # Patch get_logger to return our fake logger
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    # Patch format_markdown_header to a deterministic value
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.format_markdown_header", lambda h: "Intro-Header")

    question = "What is X?"
    response = "  This is the answer.  "
    relevant_sections = [
        {"file_name": "/docs/guide.md", "relevant_section_header_string": "Intro"},
        {"file_name": "README.txt", "relevant_section_header_string": ""},
    ]
    supported_suffixes = [".md", ".txt"]
    # base_url_prefix purposely has a trailing slash to test strip('/').
    base_url_prefix = "https://example.com/"
    base_url_suffix = "?view=1"

    out = format_markdown_q_and_a_response(
        question, response, relevant_sections, supported_suffixes, base_url_prefix, base_url_suffix
    )

    # Basic structure
    assert "### Question:" in out and question in out
    assert "### Answer:" in out and "This is the answer." in out
    assert "#### Relevant Sources:" in out

    # First entry: has header -> should include fragment with #Intro-Header
    assert "> - https://example.com/docs/guide.md?view=1#Intro-Header" in out

    # Second entry: no header -> should include file link without fragment
    assert "> - https://example.com/README.txt?view=1" in out

    # No warnings or exceptions should have been logged in this successful path
    assert fake_logger.warnings == []
    assert fake_logger.exceptions == []


def test_format_markdown_q_and_a_response_warn_and_exception_round_087(monkeypatch):
    """
    Cover the branch where an unsupported extension triggers a warning and then a
    later call into format_markdown_header raises, which should be caught by
    the outer try and result in an empty string return while logging an exception.
    """
    fake_logger = FakeLogger()

    # Patch get_logger to return our fake logger
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: fake_logger)

    # Patch format_markdown_header to raise to force the exception path
    def raising_header(h):
        raise RuntimeError("boom in header")

    monkeypatch.setattr("pr_agent.tools.pr_help_docs.format_markdown_header", raising_header)

    question = "Q"
    response = "A"

    # First section has unsupported extension -> should trigger warning and be skipped
    # Second section has supported extension but format_markdown_header will raise -> outer try catches and returns ""
    relevant_sections = [
        {"file_name": "binary.exe", "relevant_section_header_string": "something"},
        {"file_name": "docs/manual.md", "relevant_section_header_string": "Header"},
    ]
    supported_suffixes = [".md"]
    base_url_prefix = ""  # empty to also cover the branch where base_url_prefix is falsy
    base_url_suffix = ""

    out = format_markdown_q_and_a_response(
        question, response, relevant_sections, supported_suffixes, base_url_prefix, base_url_suffix
    )

    # Because raising_header raises, outer exception handler should return empty string
    assert out == ""

    # Warning should have been logged for the unsupported extension
    assert any("Unsupported file extension" in w for w in fake_logger.warnings)
    assert any("binary.exe" in w for w in fake_logger.warnings)

    # An exception should have been logged
    assert any("Unexpected exception thrown" in e for e in fake_logger.exceptions)
