# file: pr_agent/tools/pr_line_questions.py:103-149
# asked: {"lines": [109, 110, 111, 114, 115, 116, 118, 120, 123, 124, 125, 128, 129, 131, 132, 133, 136, 137, 138, 141, 142, 143, 145, 147, 148, 149], "branches": [[114, 115], [114, 118], [124, 125], [124, 136], [128, 129], [128, 131], [136, 137], [136, 145]]}
# gained: {"lines": [109, 110, 111, 114, 115, 116, 118, 120, 123, 124, 125, 128, 129, 131, 132, 133, 136, 137, 138, 141, 142, 143, 147, 148, 149], "branches": [[114, 115], [114, 118], [124, 125], [124, 136], [128, 129], [128, 131], [136, 137]]}

import pytest
import types

import pr_agent.tools.pr_line_questions as pr_mod
from pr_agent.tools.pr_line_questions import PR_LineQuestions


class FakeLogger:
    def __init__(self):
        self.error_calls = []
        self.info_calls = []

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))


class SimpleUser:
    def __init__(self, login):
        self.login = login


class Comment:
    def __init__(self, body, id_, user=None):
        self.body = body
        self.id = id_
        self.user = user


def make_instance_with_git_provider(get_review_thread_comments_callable):
    # Create instance without running __init__
    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    # attach minimal git_provider with required method
    class GP:
        def get_review_thread_comments(self, comment_id):
            return get_review_thread_comments_callable(comment_id)
    inst.git_provider = GP()
    return inst


def test_missing_settings_returns_empty_and_logs_error(monkeypatch):
    fake_logger = FakeLogger()
    # Monkeypatch get_settings to return missing parameters
    monkeypatch.setattr(pr_mod, "get_settings", lambda: {"comment_id": "", "file_name": "", "line_end": ""})
    monkeypatch.setattr(pr_mod, "get_logger", lambda: fake_logger)

    inst = PR_LineQuestions.__new__(PR_LineQuestions)
    # No git_provider needed because early return happens before it's used
    result = inst._load_conversation_history()

    assert result == ""
    # Ensure an error was logged with the expected message
    assert fake_logger.error_calls, "Expected error to be logged for missing params"
    # Check the first positional argument of the first error call
    logged_msg = fake_logger.error_calls[0][0][0]
    assert "Missing required parameters for conversation history" in logged_msg


def test_successful_history_builds_string_and_logs_info(monkeypatch):
    fake_logger = FakeLogger()
    # valid settings
    monkeypatch.setattr(pr_mod, "get_settings", lambda: {"comment_id": "c1", "file_name": "f.py", "line_end": "10"})
    monkeypatch.setattr(pr_mod, "get_logger", lambda: fake_logger)

    # Prepare comments: one empty body, one with same id as comment_id (should be skipped),
    # one with user having login, one with user missing login attr (fallback to 'Unknown')
    comments = [
        Comment("", "x", SimpleUser("u0")),               # empty body -> skip
        Comment("Ignored", "c1", SimpleUser("u1")),        # same id as comment_id -> skip
        Comment("  \n\t", "c2", SimpleUser("u2")),        # whitespace only -> skip
        Comment("First comment", "c3", SimpleUser("alice")),  # included
        Comment("Second comment", "c4", types.SimpleNamespace()),  # included, user has no login -> Unknown
    ]

    def get_comments(cid):
        # ensure the function receives the comment_id passed from settings
        assert cid == "c1"
        return comments

    inst = make_instance_with_git_provider(get_comments)

    result = inst._load_conversation_history()

    # Expect two filtered comments formatted as numbered list
    expected = "1. alice: First comment\n2. Unknown: Second comment"
    assert result == expected
    # Ensure info logged about number of loaded comments
    assert fake_logger.info_calls, "Expected info to be logged about loaded comments"
    info_msg = fake_logger.info_calls[0][0][0]
    assert "Loaded 2 comments" in info_msg


def test_exception_in_get_review_thread_comments_logs_and_returns_empty(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(pr_mod, "get_settings", lambda: {"comment_id": "c1", "file_name": "f.py", "line_end": "10"})
    monkeypatch.setattr(pr_mod, "get_logger", lambda: fake_logger)

    def raise_err(cid):
        raise RuntimeError("boom")

    inst = make_instance_with_git_provider(raise_err)

    result = inst._load_conversation_history()

    assert result == ""
    # Ensure error logged about processing conversation history with the exception message
    assert fake_logger.error_calls, "Expected an error log when exception raised"
    err_msg = fake_logger.error_calls[0][0][0]
    assert "Error processing conversation history" in err_msg
    assert "boom" in err_msg
