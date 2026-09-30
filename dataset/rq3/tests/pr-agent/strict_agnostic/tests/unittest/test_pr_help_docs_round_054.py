import pytest
from pr_agent.tools.pr_help_docs import return_document_headings


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.exceptions = []

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def test_return_document_headings_md_round_054():
    # Markdown: lines starting with # should be captured (deduplicated)
    text = "# Head1\nNot heading\n## Head2\n# Head1\n"
    result = return_document_headings(text, '.md')
    # Order is not guaranteed because a set is used; compare as a set
    assert set(result.split('\n')) == {"# Head1", "## Head2"}


def test_return_document_headings_rst_round_054(monkeypatch):
    # RST: marker lines consisting of the same character should underline headings above them
    dummy = DummyLogger()
    monkeypatch.setattr('pr_agent.tools.pr_help_docs.get_logger', lambda: dummy)

    # Construct lines so there is a marker at index 0 (should not produce a heading)
    # and two valid underline markers that should capture the preceding headings.
    lines = [
        '----',          # idx 0 marker -> should NOT add a heading (no previous content)
        '',
        'Title',         # idx 2 (will be captured by idx 3 marker)
        '-----',         # idx 3 marker -> captures 'Title'
        'Short',         # idx 4 (will be captured by idx 5 marker)
        '----------',    # idx 5 marker -> captures 'Short'
    ]
    text = '\n'.join(lines)

    result = return_document_headings(text, '.rst')
    assert set(result.split('\n')) == {"Title", "Short"}
    # ensure no empty heading was added from the top marker
    assert '' not in set(result.split('\n'))


def test_return_document_headings_empty_or_nontext_round_054(monkeypatch):
    # When text is empty or has no alphabetic characters, function should log an error and return empty string
    dummy = DummyLogger()
    monkeypatch.setattr('pr_agent.tools.pr_help_docs.get_logger', lambda: dummy)

    assert return_document_headings('', '.md') == ''
    assert return_document_headings('1234567890  !@#$', '.md') == ''
    # Expect at least two error calls (one per invocation)
    assert len(dummy.errors) >= 2


def test_return_document_headings_unsupported_ext_round_054(monkeypatch):
    # Unsupported extension should log an error and return empty string
    dummy = DummyLogger()
    monkeypatch.setattr('pr_agent.tools.pr_help_docs.get_logger', lambda: dummy)

    assert return_document_headings('some valid text', '.txt') == ''
    # Confirm logger.error was called for unsupported extension
    assert any('Unsupported file extension' in msg for msg in dummy.errors), dummy.errors
