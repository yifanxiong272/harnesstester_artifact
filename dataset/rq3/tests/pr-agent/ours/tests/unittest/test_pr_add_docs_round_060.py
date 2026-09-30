import types
import builtins
from types import SimpleNamespace
import pytest

from pr_agent.tools.pr_add_docs import PRAddDocs

# We will call the unbound function PRAddDocs.push_inline_docs with a fake self
push_inline_docs_fn = PRAddDocs.push_inline_docs


def test_no_docs_returns_publish_comment_round_060(monkeypatch):
    # Arrange: data with empty list should trigger publish_comment and an immediate return
    data = {"Code Documentation": []}

    published = {}

    class FakeGP:
        def publish_comment(self, msg):
            published['msg'] = msg
            return "COMMENTED"

        def publish_code_suggestions(self, docs):
            # should not be called in this scenario
            raise AssertionError("publish_code_suggestions should not be called")

    fake_self = SimpleNamespace(git_provider=FakeGP(), dedent_code=lambda *a, **k: "")

    # Patch logger and settings just in case code inspects them (verbosity not required here)
    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=0)))
    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_logger', lambda: SimpleNamespace(info=lambda *a, **k: None))

    # Act
    result = push_inline_docs_fn(fake_self, data)

    # Assert: immediate return value is the publish_comment return
    assert result == "COMMENTED"
    assert published['msg'] == 'No code documentation found to improve this PR.'


def test_docs_success_publish_round_060(monkeypatch):
    # Arrange: one well-formed doc entry; publish_code_suggestions returns True
    doc = {
        'relevant file': 'some_file.py',
        'relevant line': '42',
        'documentation': 'This function does X',
        'doc placement': '  above  '
    }
    data = {"Code Documentation": [doc]}

    # fake dedent_code returns a predictable snippet
    def fake_dedent(relevant_file, relevant_line, documentation, doc_placement, add_original_line=True):
        # assert we receive expected transformed args
        assert relevant_file == 'some_file.py'
        assert relevant_line == 42
        assert documentation == 'This function does X'
        assert doc_placement.strip() == 'above'
        # Provide a snippet that will be embedded into the suggestion body
        return 'def foo():\n    pass'

    called = {}

    class FakeGP:
        def publish_comment(self, msg):
            called['comment'] = msg
            return None

        def publish_code_suggestions(self, docs):
            # Expect a single call with our built docs list
            called['docs'] = docs
            return True

    # Want to capture logger.info calls when verbosity >=2
    logger = SimpleNamespace(info=lambda m: called.setdefault('log', []).append(m))
    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_logger', lambda: logger)
    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=2)))

    fake_self = SimpleNamespace(git_provider=FakeGP(), dedent_code=fake_dedent)

    # Act
    result = push_inline_docs_fn(fake_self, data)

    # Assert: function completes (returns None) and publish_code_suggestions called with expected payload
    assert result is None

    assert 'docs' in called, 'publish_code_suggestions was not called'
    docs_arg = called['docs']
    assert isinstance(docs_arg, list) and len(docs_arg) == 1
    doc_payload = docs_arg[0]

    # Body contains the dedented snippet in the expected suggestion wrapper
    assert '**Suggestion:** Proposed documentation' in doc_payload['body']
    assert 'def foo()' in doc_payload['body']
    assert doc_payload['relevant_file'] == 'some_file.py'
    assert doc_payload['relevant_lines_start'] == 42
    assert doc_payload['relevant_lines_end'] == 42

    # Verbosity logging should have recorded the add_docs message
    assert any('add_docs' in str(m) for m in called.get('log', []))


def test_docs_publish_failure_falls_back_and_exception_logging_round_060(monkeypatch):
    # Arrange: include one good doc and one broken doc to hit both normal flow and except path
    good_doc = {
        'relevant file': 'good.py',
        'relevant line': '10',
        'documentation': 'Ok',
        'doc placement': 'below'
    }
    # broken doc will raise when int(...) is attempted
    bad_doc = {
        'relevant file': 'bad.py',
        'relevant line': 'NOT_AN_INT',
        # missing 'documentation' key will also cause KeyError if reached, but int() will already raise
    }

    data = {"Code Documentation": [good_doc, bad_doc]}

    # dedent_code for good doc
    def fake_dedent(relevant_file, relevant_line, documentation, doc_placement, add_original_line=True):
        return f"# {relevant_file}:{relevant_line}\n{documentation}"

    calls = []

    class FakeGP:
        def publish_comment(self, msg):
            calls.append(('comment', msg))
            return None

        def publish_code_suggestions(self, docs):
            # First call (full docs list) => failure; subsequent calls => success
            calls.append(('publish', docs))
            # If a list with more than 1 entry was passed, treat as initial bulk publish
            if len(docs) > 1:
                return False
            return True

    # Capture logger messages
    logger_messages = []

    def logger_info(msg):
        logger_messages.append(msg)

    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_logger', lambda: SimpleNamespace(info=logger_info))
    # Set verbosity high so that both the add_docs and except logging paths are exercised
    monkeypatch.setattr('pr_agent.tools.pr_add_docs.get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=2)))

    fake_self = SimpleNamespace(git_provider=FakeGP(), dedent_code=fake_dedent)

    # Act
    result = push_inline_docs_fn(fake_self, data)

    # Assert: after initial bulk publish fails, publish_code_suggestions should be called per doc
    publish_calls = [c for c in calls if c[0] == 'publish']
    # First publish call: bulk with only the successfully parsed doc(s). The broken doc may have been skipped due to exception.
    assert len(publish_calls) >= 1

    # Because the broken doc triggers an exception, we expect an except log mentioning the bad doc
    assert any('Could not parse code docs' in str(m) for m in logger_messages), f"logger did not record except message: {logger_messages}"

    # Also expect the failure message when initial bulk publish returned False
    assert any('Failed to publish code docs' in str(m) for m in logger_messages), f"did not see failure-to-publish log: {logger_messages}"

    # Function should return None (normal completion)
    assert result is None
