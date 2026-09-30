import types
import pytest
from types import SimpleNamespace

import pr_agent.tools.pr_line_questions as plq_mod
from pr_agent.tools.pr_line_questions import PR_LineQuestions


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class DummyGitProvider:
    def __init__(self, comments=None, raise_exc=False):
        self._comments = comments or []
        self._raise = raise_exc

    def get_review_thread_comments(self, comment_id):
        if self._raise:
            raise Exception("boom")
        # Return the comments as-is (they should be objects with .body, .id, .user)
        return self._comments


def make_comment(id, body, user_login=None):
    user = SimpleNamespace()
    if user_login is not None:
        user.login = user_login
    # else user has no login attribute to exercise 'Unknown' branch
    return SimpleNamespace(id=id, body=body, user=user)


def test_missing_settings_round_069(monkeypatch):
    """If required settings are missing, should log an error and return empty string"""
    dummy_logger = DummyLogger()
    # patch module-level get_settings and get_logger
    monkeypatch.setattr(plq_mod, "get_settings", lambda: {})
    monkeypatch.setattr(plq_mod, "get_logger", lambda: dummy_logger)

    # build PR_LineQuestions instance without calling __init__ to avoid side effects
    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    inst.git_provider = DummyGitProvider(comments=[])

    result = PR_LineQuestions._load_conversation_history(inst)

    assert result == ""
    # ensure logger.error was called at least once with the missing parameters message
    assert any("Missing required parameters" in e for e in dummy_logger.errors)


def test_empty_thread_comments_round_069(monkeypatch):
    """When review thread has no comments, should return empty string (no conversation)"""
    dummy_logger = DummyLogger()
    monkeypatch.setattr(plq_mod, "get_settings", lambda: {
        "comment_id": "c1",
        "file_name": "f.py",
        "line_end": 10,
    })
    monkeypatch.setattr(plq_mod, "get_logger", lambda: dummy_logger)

    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    inst.git_provider = DummyGitProvider(comments=[])

    result = PR_LineQuestions._load_conversation_history(inst)

    assert result == ""
    # no info logs about loaded comments
    assert dummy_logger.infos == []


def test_filtered_and_formatted_comments_round_069(monkeypatch):
    """Comments should be filtered (skip empties and current comment) and formatted correctly."""
    dummy_logger = DummyLogger()
    monkeypatch.setattr(plq_mod, "get_settings", lambda: {
        "comment_id": "c2",
        "file_name": "f.py",
        "line_end": 20,
    })
    monkeypatch.setattr(plq_mod, "get_logger", lambda: dummy_logger)

    # Prepare comments:
    # - comment with empty body (skipped)
    # - comment with same id as current (skipped)
    # - comment with login 'alice'
    # - comment with user missing login -> 'Unknown'
    comments = [
        make_comment("c0", "   ", user_login="bob"),
        make_comment("c2", "I'm the current comment and should be skipped", user_login="me"),
        make_comment("c3", "Hello", user_login="alice"),
        make_comment("c4", "Bye", user_login=None),
    ]

    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    inst.git_provider = DummyGitProvider(comments=comments)

    result = PR_LineQuestions._load_conversation_history(inst)

    # Expect two lines, numbered and with authors
    expected_lines = ["1. alice: Hello", "2. Unknown: Bye"]
    assert result.splitlines() == expected_lines

    # ensure info log mentions loaded 2 comments
    assert any("Loaded 2 comments" in s for s in dummy_logger.infos)


def test_exception_in_provider_round_069(monkeypatch):
    """If provider raises, should catch, log error, and return empty string."""
    dummy_logger = DummyLogger()
    monkeypatch.setattr(plq_mod, "get_settings", lambda: {
        "comment_id": "c9",
        "file_name": "f.py",
        "line_end": 30,
    })
    monkeypatch.setattr(plq_mod, "get_logger", lambda: dummy_logger)

    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    inst.git_provider = DummyGitProvider(raise_exc=True)

    result = PR_LineQuestions._load_conversation_history(inst)

    assert result == ""
    assert any("Error processing conversation history" in e for e in dummy_logger.errors)
