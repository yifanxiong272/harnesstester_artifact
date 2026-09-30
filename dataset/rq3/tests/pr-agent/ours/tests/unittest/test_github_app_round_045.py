import pytest
import types
from types import SimpleNamespace
import asyncio

from pr_agent.servers import github_app
from pr_agent.identity_providers.identity_provider import Eligibility

@pytest.mark.asyncio
async def test_missing_comment_round_045():
    # Body without a "comment" key should return an empty dict early
    body = {"issue": {"pull_request": {"url": "http://api/pr/1"}}}
    result = await github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="alice",
        sender_id="alice-id",
        action="created",
        log_context={},
        agent=SimpleNamespace(),
    )
    assert result == {}, "Expected empty dict when no comment is present"


@pytest.mark.asyncio
async def test_handle_ask_line_comment_round_045(monkeypatch):
    # Prepare a comment that starts with an image quote and contains /ask
    raw_comment = "> ![image] context before /ask do_something arg"
    comment_id = 321
    api_url = "http://api.example/pr/2"

    body = {
        "comment": {
            "body": raw_comment,
            "pull_request_url": api_url,
            "id": comment_id,
            "subject_type": "line",
        }
    }

    # Patch handle_line_comments to assert it's called and to return a modified body
    def fake_handle_line_comments(passed_body, passed_comment_body):
        # ensure it's receiving the formatted comment (starting with /ask)
        assert isinstance(passed_comment_body, str)
        assert passed_comment_body.startswith("/ask")
        return passed_comment_body + " [line-handled]"

    monkeypatch.setattr(github_app, "handle_line_comments", fake_handle_line_comments)

    # Create a fake provider that records add_eyes_reaction calls
    class FakeProvider:
        def __init__(self):
            self.calls = []

        def add_eyes_reaction(self, cid, disable_eyes=False):
            # record calls for assertion
            self.calls.append({"id": cid, "disable_eyes": disable_eyes})

    fake_provider = FakeProvider()
    monkeypatch.setattr(github_app, "get_git_provider_with_context", lambda pr_url: fake_provider)

    # get_logger: provide .info, .error, and a contextualize() context manager
    class FakeLogger:
        def info(self, *args, **kwargs):
            # keep deterministic: no-op
            pass

        def error(self, *args, **kwargs):
            # keep deterministic: no-op
            pass

        class _Ctx:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def contextualize(self, **kwargs):
            return FakeLogger._Ctx()

    monkeypatch.setattr(github_app, "get_logger", lambda: FakeLogger())

    # Identity provider: ensure verify_eligibility returns something not equal to NOT_ELIGIBLE
    class FakeIdentityProvider:
        def verify_eligibility(self, provider_name, sender_id, api_url_arg):
            # return a sentinel that is not Eligibility.NOT_ELIGIBLE
            return "ELIGIBLE_SENTINEL"

    monkeypatch.setattr(github_app, "get_identity_provider", lambda: FakeIdentityProvider())

    # Create an agent whose handle_request records the inputs and calls the notify callable
    class MockAgent:
        def __init__(self):
            self.called = False
            self.received = None

        async def handle_request(self, api_url_arg, comment_body_arg, notify=None):
            # record values for assertions
            self.called = True
            self.received = (api_url_arg, comment_body_arg)
            # call notify to simulate adding reaction
            if notify:
                # notify could be passed as a kwarg or positional; ensure it is callable
                notify()

    agent = MockAgent()

    # Run the function under test
    await github_app.handle_comments_on_pr(
        body=body,
        event="issue_comment",
        sender="bob",
        sender_id="bob-id",
        action="created",
        log_context={},
        agent=agent,
    )

    # Assertions: agent was invoked with API URL and the comment body returned by fake_handle_line_comments
    assert agent.called is True, "Agent.handle_request should have been awaited"
    assert agent.received is not None
    assert agent.received[0] == api_url
    # after formatting and fake_handle_line_comments, the body should contain the marker
    assert agent.received[1].endswith("[line-handled]"), "Expected handle_line_comments to transform the comment_body"

    # verify provider.add_eyes_reaction was called with the comment id and disable_eyes True (because subject_type == 'line')
    assert fake_provider.calls == [{"id": comment_id, "disable_eyes": True}]
