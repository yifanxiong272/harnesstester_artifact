import asyncio
from types import SimpleNamespace

import pr_agent.servers.github_app as github_app

# Tests generated to exercise branches in handle_comments_on_pr

async def _run_coro(coro):
    return await coro

# 1) missing 'comment' -> early return {}
def test_missing_comment_round_045():
    body = {"issue": {}}  # no 'comment' key
    result = asyncio.run(_run_coro(github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="u",
        sender_id="1",
        action="created",
        log_context={},
        agent=SimpleNamespace(),
    )))
    assert result == {}


# 2) comment present but body is a string not starting with '/' -> early return {}
def test_comment_not_command_round_045():
    body = {"comment": {"body": "hello world"}}
    result = asyncio.run(_run_coro(github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="u",
        sender_id="1",
        action="created",
        log_context={},
        agent=SimpleNamespace(),
    )))
    assert result == {}


# Helper fakes used by other tests
class FakeProvider:
    def __init__(self):
        self.called = None

    def add_eyes_reaction(self, comment_id, disable_eyes=False):
        # record the call for assertions
        self.called = {"comment_id": comment_id, "disable_eyes": disable_eyes}


class FakeIdentityProvider:
    def __init__(self, return_value):
        self._rv = return_value

    def verify_eligibility(self, provider_name, sender_id, api_url):
        # deterministic, returns configured value
        return self._rv


class FakeAgent:
    def __init__(self):
        self.called = None

    async def handle_request(self, api_url, comment_body, notify=None):
        # record parameters and exercise the notify callable if provided
        self.called = {"api_url": api_url, "comment_body": comment_body}
        if notify:
            # call notify to trigger provider.add_eyes_reaction side effect
            notify()


# 3) issue.pull_request.url path -> agent.handle_request invoked and provider.add_eyes_reaction called
def test_issue_pull_request_eligible_round_045():
    fake_provider = FakeProvider()
    fake_agent = FakeAgent()

    # patch provider and identity provider into module
    github_app.get_git_provider_with_context = lambda pr_url: fake_provider
    github_app.get_identity_provider = lambda: FakeIdentityProvider(github_app.Eligibility.ELIGIBLE)

    body = {
        "comment": {"body": "/do something", "id": 123},
        "issue": {"pull_request": {"url": "https://api.github.com/pr/1"}}
    }
    log_context = {}

    asyncio.run(_run_coro(github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="user",
        sender_id="42",
        action="created",
        log_context=log_context,
        agent=fake_agent,
    )))

    # agent was invoked with api_url from issue.pull_request.url and original comment
    assert fake_agent.called is not None
    assert fake_agent.called["api_url"] == "https://api.github.com/pr/1"
    assert fake_agent.called["comment_body"] == "/do something"

    # provider.add_eyes_reaction should have been called with the comment id and disable_eyes False
    assert fake_provider.called == {"comment_id": 123, "disable_eyes": False}


# 4) comment path with an image '/ask' style comment and subject_type 'line' triggers handle_line_comments and disable_eyes True
def test_comment_ask_line_subject_round_045():
    fake_provider = FakeProvider()
    fake_agent = FakeAgent()

    # monkeypatch provider and identity provider
    github_app.get_git_provider_with_context = lambda pr_url: fake_provider
    github_app.get_identity_provider = lambda: FakeIdentityProvider(github_app.Eligibility.ELIGIBLE)

    # monkeypatch handle_line_comments to simulate line-processing
    original_handle_line_comments = github_app.handle_line_comments
    github_app.handle_line_comments = lambda body, cb: "LINE_HANDLED"

    # Build a comment that matches the reformatting condition and has pull_request_url and subject_type=line
    # Use a single-line string with explicit newline to avoid unterminated literal issues
    comment_text = "> ![image] foo /ask do-this\nmore"

    body = {
        "comment": {
            "body": comment_text,
            "id": 999,
            "pull_request_url": "https://api.github.com/pr/2",
            "subject_type": "line",
        }
    }

    try:
        asyncio.run(_run_coro(github_app.handle_comments_on_pr(
            body=body,
            event="issue_comment",
            sender="user",
            sender_id="99",
            action="created",
            log_context={},
            agent=fake_agent,
        )))

        # agent should have been called with the processed comment (our stub returns LINE_HANDLED)
        assert fake_agent.called is not None
        assert fake_agent.called["api_url"] == "https://api.github.com/pr/2"
        assert fake_agent.called["comment_body"] == "LINE_HANDLED"

        # provider.add_eyes_reaction should have been called with disable_eyes True due to line comment handling
        assert fake_provider.called == {"comment_id": 999, "disable_eyes": True}
    finally:
        # restore original implementation to avoid side-effects for other tests
        github_app.handle_line_comments = original_handle_line_comments


# 5) user not eligible -> verify_eligibility returns NOT_ELIGIBLE and agent.handle_request must not be called
def test_user_not_eligible_round_045():
    fake_provider = FakeProvider()
    fake_agent = FakeAgent()

    github_app.get_git_provider_with_context = lambda pr_url: fake_provider
    github_app.get_identity_provider = lambda: FakeIdentityProvider(github_app.Eligibility.NOT_ELIGIBLE)

    body = {
        "comment": {"body": "/cmd", "id": 555, "pull_request_url": "https://api.github.com/pr/3"}
    }

    result = asyncio.run(_run_coro(github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="someone",
        sender_id="555",
        action="created",
        log_context={},
        agent=fake_agent,
    )))

    # when not eligible, function should not invoke agent.handle_request; agent.called remains None
    assert fake_agent.called is None
    # function reaches the logging branch and returns None (no explicit return path)
    assert result is None
