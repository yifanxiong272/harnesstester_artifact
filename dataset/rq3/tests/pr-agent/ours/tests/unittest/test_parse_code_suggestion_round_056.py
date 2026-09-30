import textwrap
import pytest
from pr_agent.algo.utils import parse_code_suggestion


class DummyLogger:
    def __init__(self):
        self.messages = []

    def exception(self, msg):
        # store the message for assertions
        self.messages.append(str(msg))


def test_parse_code_suggestion_table_with_link_round_056(monkeypatch):
    """
    GFM supported path: ensure relevant_file, suggestion and relevant_line with link
    produce the expected table rows and anchor link.
    """
    logger = DummyLogger()
    # Patch the get_logger used inside the module under test
    monkeypatch.setattr('pr_agent.algo.utils.get_logger', lambda: logger)

    # Construct dict in insertion order to exercise branches 534-547 and 554-555
    code_suggestion = {
        'relevant_file': '`"/path/to/file.py"`',
        'suggestion': '   Replace X with Y   ',
        'relevant_line': '`[123](http://example.com/path)`'
    }

    out = parse_code_suggestion(code_suggestion, i=0, gfm_supported=True)

    # Basic structure checks
    assert out.startswith('<table>'), "expected table opening"
    assert out.endswith('<hr>'), "expected trailing hr"

    # relevant_file row should include the cleaned filename without backticks or quotes
    assert "relevant file" in out
    assert "/path/to/file.py" in out

    # suggestion should be wrapped in <strong> tags and trimmed
    assert '<strong>' in out
    assert 'Replace X with Y' in out

    # relevant_line should produce an anchor link with the link and the line number text
    assert "<a href='http://example.com/path'>123</a>" in out


def test_parse_code_suggestion_table_linkless_and_exception_round_056(monkeypatch):
    """
    GFM supported path where relevant_line value causes an exception (None).
    Verify the exception is caught and get_logger().exception is invoked, and table
    wrapper is still produced.
    """
    logger = DummyLogger()
    monkeypatch.setattr('pr_agent.algo.utils.get_logger', lambda: logger)

    # Put relevant_line with a non-str value to force an AttributeError on split()
    code_suggestion = {
        'relevant_file': '`fileX.py`',
        'relevant_line': None,  # will cause exception when .split is attempted
    }

    out = parse_code_suggestion(code_suggestion, i=0, gfm_supported=True)

    # Should still return a table wrapper even if inner parsing failed
    assert out.startswith('<table>')
    assert out.endswith('<hr>')

    # Ensure logger.exception was called with an explanatory message
    assert len(logger.messages) >= 1
    assert any('Failed to parse code suggestion' in m for m in logger.messages)


def test_parse_code_suggestion_non_gfm_branch_and_code_example_round_056(monkeypatch):
    """
    Non-GFM branch: exercise the dict-as-value (code example) branch and
    the relevant_file string-key branch, plus the normal-key path that
    triggers the rstrip and appended whitespace behavior.
    """
    # patch logger though not expected to be used here; keep deterministic
    logger = DummyLogger()
    monkeypatch.setattr('pr_agent.algo.utils.get_logger', lambda: logger)

    code_suggestion = {
        'code_example': {'before': 'line_before = 1', 'after': 'line_after = 2'},
        'Some_Relevant_File': '  src/module.py  ',
        'note': 'a short note\n'
    }

    out = parse_code_suggestion(code_suggestion, i=0, gfm_supported=False)

    # Code example should render fenced code blocks and labels
    assert '```' in out
    assert '**code_example' in out or '- **code_example' in out
    assert '**before' in out and '**after' in out

    # Relevant file branch (non-gfm) should include the key and value
    assert 'Some_Relevant_File' in out
    assert 'src/module.py' in out

    # The note key should be present; formatting code ensures no raw trailing newlines
    assert '**note:' in out or '   **note:' in out
