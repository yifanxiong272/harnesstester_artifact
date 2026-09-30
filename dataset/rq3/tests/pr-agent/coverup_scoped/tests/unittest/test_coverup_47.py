# file: pr_agent/git_providers/github_provider.py:371-392
# asked: {"lines": [372, 373, 374, 376, 377, 378, 379, 382, 383, 385, 386, 387, 388, 389, 390, 391, 392], "branches": [[372, 373], [372, 376], [376, 377], [376, 379], [382, 383], [382, 385], [386, 387], [386, 388], [389, 390], [389, 391]]}
# gained: {"lines": [372, 373, 374, 376, 377, 378, 379, 382, 383, 385, 386, 387, 388, 389, 390, 391, 392], "branches": [[372, 373], [372, 376], [376, 377], [376, 379], [382, 383], [382, 385], [386, 387], [389, 390]]}

import types
from types import SimpleNamespace
import pytest

from pr_agent.git_providers.github_provider import GithubProvider

class DummySettings:
    def __init__(self, publish_output_progress=True):
        self.config = SimpleNamespace(publish_output_progress=publish_output_progress)
        self.github = SimpleNamespace(ratelimit_retries=1)
    def get(self, key, default=None):
        if key == 'GITHUB.BASE_URL':
            return 'https://api.github.com'
        return default

def make_logger(calls):
    class Logger:
        def debug(self, msg):
            calls.append(('debug', msg))
        def error(self, msg):
            calls.append(('error', msg))
    return Logger()

def make_provider():
    # Create instance without calling __init__ to avoid side-effects
    p = GithubProvider.__new__(GithubProvider)
    # minimal attributes used by publish_comment
    p.pr = None
    p.issue_main = None
    p.max_comment_chars = 65000
    p.github_user_id = None
    p.limit_output_characters = lambda s, n: s
    return p

def test_publish_comment_no_context(monkeypatch):
    calls = []
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_logger', lambda: make_logger(calls))
    provider = make_provider()
    provider.pr = None
    provider.issue_main = None

    res = provider.publish_comment("hello world")
    assert res is None
    # logger should have been called with an error
    assert any(level == 'error' and "Cannot publish a comment if missing PR/Issue context" in msg for level, msg in calls)

def test_publish_comment_temporary_skipped_when_disabled(monkeypatch):
    calls = []
    # publish_output_progress False should skip temporary comment
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_settings', lambda: DummySettings(publish_output_progress=False))
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_logger', lambda: make_logger(calls))

    provider = make_provider()
    # ensure first "no context" branch is not hit by providing a PR object
    provider.pr = SimpleNamespace()
    provider.issue_main = None

    res = provider.publish_comment("temp comment", is_temporary=True)
    assert res is None
    # logger should have debugged the skipping
    assert any(level == 'debug' and "Skipping publish_comment for temporary comment" in msg for level, msg in calls)

def test_publish_comment_issue_main_uses_issue_create(monkeypatch):
    # ensure settings allow publishing (so not skipped)
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_settings', lambda: DummySettings(publish_output_progress=True))
    calls = []
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_logger', lambda: make_logger(calls))

    created = []
    class IssueMock:
        def create_comment(self, text):
            created.append(text)
            return {"result": "ok", "text": text}

    provider = make_provider()
    provider.pr = None
    provider.issue_main = IssueMock()
    provider.limit_output_characters = lambda s, n: s[:5]  # simulate truncation

    res = provider.publish_comment("1234567890", is_temporary=False)
    assert res == {"result": "ok", "text": "12345"}
    # ensure issue.create_comment was called with truncated text
    assert created == ["12345"]

def test_publish_comment_pr_appends_response_and_sets_user(monkeypatch):
    # allow publishing of temporary comments
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_settings', lambda: DummySettings(publish_output_progress=True))
    monkeypatch.setattr('pr_agent.git_providers.github_provider.get_logger', lambda: make_logger([]))

    # Create a response object with user.login
    class User:
        def __init__(self, login):
            self.login = login

    class Response:
        def __init__(self, login):
            self.user = User(login)
            # is_temporary will be set by publish_comment

    # pr mock without comments_list attribute initially
    created = []
    def create_issue_comment(text):
        created.append(text)
        return Response("bot-user")

    pr_mock = SimpleNamespace(create_issue_comment=create_issue_comment)

    provider = make_provider()
    provider.issue_main = None
    provider.pr = pr_mock
    provider.limit_output_characters = lambda s, n: s  # identity

    res = provider.publish_comment("final message", is_temporary=True)
    # returned response
    assert isinstance(res, Response)
    # github_user_id should be set from response.user.login
    assert provider.github_user_id == "bot-user"
    # response should have is_temporary attribute set to True
    assert getattr(res, "is_temporary", None) is True
    # pr should now have comments_list containing the response
    assert hasattr(provider.pr, "comments_list")
    assert provider.pr.comments_list[-1] is res
    # ensure the comment text passed into create_issue_comment was as expected
    assert created == ["final message"]
