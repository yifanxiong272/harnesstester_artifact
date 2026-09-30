import types
import pytest

import pr_agent.git_providers.github_provider as gp


class DummyRequester:
    def __init__(self, get_existing=None, raise_on_get=False):
        # get_existing should be the list returned for GET
        self.get_existing = get_existing if get_existing is not None else []
        self.calls = []
        self.raise_on_get = raise_on_get

    def requestJsonAndCheck(self, method, url, input=None):
        # Record call deterministically
        self.calls.append({"method": method, "url": url, "input": input})
        if method == "GET":
            if self.raise_on_get:
                raise Exception("boom")
            return (None, self.get_existing)
        # For PATCH/POST return a simple success payload
        return (None, {"result": "ok", "method": method})


def make_self_with(pr_url, existing_comments=None, raise_on_get=False):
    requester = DummyRequester(get_existing=existing_comments, raise_on_get=raise_on_get)
    pr = types.SimpleNamespace(url=pr_url, _requester=requester)
    # Build a minimal self object with attributes used by the method under test
    s = types.SimpleNamespace()
    s.pr = pr
    s.last_commit_id = types.SimpleNamespace(sha="commit-sha-1")
    # limit_output_characters should be called and its return used
    s.limit_output_characters = lambda body, max_chars: (body + "-trunc") if body is not None else body
    s.max_comment_chars = 80
    s.deployment_type = 'app'
    s.github_user_id = 'bot-user'
    s.base_url = "https://api.github.com"
    s.repo = "org/repo"
    return s, requester


def test_publish_file_comments_app_patch_round_063(monkeypatch):
    # Prepare an existing comment that matches by path and contains the app name in user login
    existing = [
        {"id": 42, "user": {"login": "myapp-bot"}, "subject_type": "file", "path": "foo.py"}
    ]
    s, requester = make_self_with("https://api.github.com/repos/org/repo/pulls/1", existing_comments=existing)

    # Patch get_settings to provide the app name used in creation checks
    monkeypatch.setattr(gp, "get_settings", lambda: {"GITHUB.APP_NAME": "MyApp"})

    # Patch logger to ensure no real logging, but allow harmless calls
    monkeypatch.setattr(gp, "get_logger", lambda: types.SimpleNamespace(error=lambda msg: None))

    # Input file comment that should match and cause a PATCH
    file_comments = [{"path": "foo.py", "body": "hello world"}]

    result = gp.GithubProvider.publish_file_comments(s, file_comments)

    assert result is True

    # Verify that a PATCH call was made to the existing comment id and that the body was truncated
    patch_calls = [c for c in requester.calls if c["method"] == "PATCH"]
    assert len(patch_calls) == 1, f"expected one PATCH call, got {requester.calls}"
    patch = patch_calls[0]
    assert str(existing[0]["id"]) in patch["url"].split("/") or patch["url"].endswith(str(existing[0]["id"]))
    # Body should be the transformed value from limit_output_characters
    assert patch["input"] == {"body": "hello world-trunc"}


def test_publish_file_comments_no_existing_post_round_063(monkeypatch):
    # No existing comments -> should POST
    s, requester = make_self_with("https://api.github.com/repos/org/repo/pulls/2", existing_comments=[])

    # Use user deployment type to exercise that branch when not matching any existing comment
    s.deployment_type = 'user'
    s.github_user_id = 'some-user'

    monkeypatch.setattr(gp, "get_settings", lambda: {"GITHUB.APP_NAME": "Irrelevant"})
    monkeypatch.setattr(gp, "get_logger", lambda: types.SimpleNamespace(error=lambda msg: None))

    file_comments = [{"path": "bar.py", "body": "body text"}]

    result = gp.GithubProvider.publish_file_comments(s, file_comments)

    assert result is True

    # Verify that a POST call was made to pr.url/comments and that commit_id was injected
    post_calls = [c for c in requester.calls if c["method"] == "POST"]
    assert len(post_calls) == 1
    post = post_calls[0]
    assert post["url"].endswith("/comments")
    # The posted input should include the commit_id set from last_commit_id.sha and the transformed body
    assert post["input"]["commit_id"] == s.last_commit_id.sha
    assert post["input"]["body"] == "body text-trunc"
    assert post["input"]["path"] == "bar.py"


def test_publish_file_comments_exception_logs_and_returns_false_round_063(monkeypatch):
    # Make the GET raise an exception to exercise the except block
    s, requester = make_self_with("https://api.github.com/repos/org/repo/pulls/3", existing_comments=[], raise_on_get=True)

    # Capture logger error messages
    logged = []
    monkeypatch.setattr(gp, "get_logger", lambda: types.SimpleNamespace(error=lambda msg: logged.append(msg)))
    monkeypatch.setattr(gp, "get_settings", lambda: {"GITHUB.APP_NAME": "Whatever"})

    file_comments = [{"path": "x.py", "body": "b"}]

    result = gp.GithubProvider.publish_file_comments(s, file_comments)

    assert result is False
    assert len(logged) == 1
    assert "Failed to publish diffview file summary" in logged[0]
