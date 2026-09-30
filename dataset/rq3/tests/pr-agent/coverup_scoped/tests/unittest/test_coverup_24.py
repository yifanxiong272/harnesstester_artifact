# file: pr_agent/tools/pr_add_docs.py:104-134
# asked: {"lines": [105, 107, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 130, 131, 132, 133, 134], "branches": [[107, 108], [107, 110], [110, 111], [110, 130], [112, 113], [112, 114], [118, 110], [118, 119], [127, 110], [127, 128], [131, 0], [131, 132], [133, 0], [133, 134]]}
# gained: {"lines": [105, 107, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 130, 131, 132, 133, 134], "branches": [[107, 108], [107, 110], [110, 111], [110, 130], [112, 113], [118, 119], [127, 128], [131, 0], [131, 132], [133, 0], [133, 134]]}

import pytest
from types import SimpleNamespace

import pr_agent.tools.pr_add_docs as pr_add_docs_module
from pr_agent.tools.pr_add_docs import PRAddDocs


class DummyLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        # ensure we always store strings
        self.infos.append(str(msg))


class DummyGitProvider:
    def __init__(self):
        self.published_comments = []
        self.published_suggestions = []

    def publish_comment(self, msg):
        self.published_comments.append(msg)
        return "PUBLISHED_COMMENT"

    def publish_code_suggestions(self, docs):
        self.published_suggestions.append(docs)
        return True


def make_settings(verbosity_level=1):
    return SimpleNamespace(config=SimpleNamespace(verbosity_level=verbosity_level))


def make_pr_instance(git_provider=None, dedent_return="NEW_SNIPPET"):
    pr = object.__new__(PRAddDocs)
    pr.git_provider = git_provider or DummyGitProvider()
    # Provide a simple dedent_code implementation used by push_inline_docs
    pr.dedent_code = lambda relevant_file, relevant_lines_start, new_code_snippet, doc_placement='after', add_original_line=False: dedent_return
    return pr


def test_push_inline_docs_no_docs(monkeypatch):
    settings_obj = make_settings(verbosity_level=1)
    fake_logger = DummyLogger()
    monkeypatch.setattr(pr_add_docs_module, "get_settings", lambda: settings_obj)
    monkeypatch.setattr(pr_add_docs_module, "get_logger", lambda: fake_logger)

    git = DummyGitProvider()
    pr = make_pr_instance(git_provider=git)

    data = {"Code Documentation": []}
    res = pr.push_inline_docs(data)

    # Should return the value from publish_comment and record the comment
    assert res == "PUBLISHED_COMMENT"
    assert git.published_comments == ["No code documentation found to improve this PR."]
    assert git.published_suggestions == []
    # No logs expected because verbosity is 1
    assert fake_logger.infos == []


def test_push_inline_docs_success(monkeypatch):
    settings_obj = make_settings(verbosity_level=2)
    fake_logger = DummyLogger()
    monkeypatch.setattr(pr_add_docs_module, "get_settings", lambda: settings_obj)
    monkeypatch.setattr(pr_add_docs_module, "get_logger", lambda: fake_logger)

    class GP(DummyGitProvider):
        def __init__(self):
            super().__init__()
            self.captured = None

        def publish_code_suggestions(self, docs):
            self.captured = docs
            self.published_suggestions.append(docs)
            return True

    git = GP()
    pr = make_pr_instance(git_provider=git, dedent_return="line1\nline2")

    doc = {
        "relevant file": " file.py ",
        "relevant line": "10",
        "documentation": "This is a doc.",
        "doc placement": " after "
    }
    data = {"Code Documentation": [doc]}

    res = pr.push_inline_docs(data)

    # push_inline_docs does not explicitly return on success path
    assert res is None
    assert git.captured is not None
    assert isinstance(git.captured, list) and len(git.captured) == 1
    suggestion = git.captured[0]
    # Check trimmed filename and integer lines
    assert suggestion["relevant_file"] == "file.py"
    assert suggestion["relevant_lines_start"] == 10
    assert suggestion["relevant_lines_end"] == 10
    # Body should contain the returned dedented snippet and suggestion markers (check substrings)
    assert "Suggestion" in suggestion["body"]
    assert "line1" in suggestion["body"]
    assert "line2" in suggestion["body"]
    # Logger should have an 'add_docs' entry
    assert any("add_docs" in s for s in fake_logger.infos)


def test_push_inline_docs_publish_fallback_and_exception(monkeypatch):
    settings_obj = make_settings(verbosity_level=2)
    fake_logger = DummyLogger()
    monkeypatch.setattr(pr_add_docs_module, "get_settings", lambda: settings_obj)
    monkeypatch.setattr(pr_add_docs_module, "get_logger", lambda: fake_logger)

    # Create a git provider that returns False on first publish_code_suggestions call
    class GP(DummyGitProvider):
        def __init__(self):
            super().__init__()
            self.calls = []

        def publish_code_suggestions(self, docs):
            # record a shallow copy for later inspection
            self.calls.append(list(docs))
            # Return False for the first call to trigger the fallback loop,
            # then True afterwards.
            return len(self.calls) > 1

    git = GP()
    pr = make_pr_instance(git_provider=git, dedent_return="SNIP-FALLBACK")

    bad_doc = {
        "relevant file": "bad.py",
        "relevant line": "not_an_int",  # will raise when int() is called
        "documentation": "ignored",
        "doc placement": "after"
    }
    good_doc = {
        "relevant file": "good.py",
        "relevant line": "20",
        "documentation": "useful doc",
        "doc placement": "before"
    }
    data = {"Code Documentation": [bad_doc, good_doc]}

    res = pr.push_inline_docs(data)

    assert res is None
    # First publish_code_suggestions call should have been with the aggregated docs list (one successful suggestion)
    assert len(git.calls) >= 2
    first_call = git.calls[0]
    # Because the bad_doc raises, only the good_doc should produce a suggestion in the aggregated call
    assert isinstance(first_call, list) and len(first_call) == 1
    suggestion = first_call[0]
    assert suggestion["relevant_file"] == "good.py"
    assert suggestion["relevant_lines_start"] == 20
    assert suggestion["relevant_lines_end"] == 20
    assert "SNIP-FALLBACK" in suggestion["body"]

    # The fallback should have attempted to publish each suggestion separately,
    # resulting in at least one more call (per-doc)
    assert len(git.calls) >= 2
    # Ensure the logger recorded the parse failure for the bad_doc and the failure message for publish
    assert any("Could not parse code docs" in s for s in fake_logger.infos)
    assert any("Failed to publish code docs" in s for s in fake_logger.infos)
