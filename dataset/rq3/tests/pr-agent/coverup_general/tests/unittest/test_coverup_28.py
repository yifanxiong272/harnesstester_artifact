# file: pr_agent/git_providers/github_provider.py:646-678
# asked: {"lines": [647, 648, 649, 651, 652, 653, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 666, 667, 669, 670, 671, 672, 673, 675, 676, 677, 678], "branches": [[651, 652], [651, 675], [656, 657], [656, 671], [660, 661], [660, 662], [662, 663], [662, 664], [664, 656], [664, 666], [671, 651], [671, 672]]}
# gained: {"lines": [647, 648, 649, 651, 652, 653, 655, 656, 657, 658, 659, 660, 661, 664, 666, 667, 669, 670, 671, 672, 673, 675, 676, 677, 678], "branches": [[651, 652], [651, 675], [656, 657], [656, 671], [660, 661], [664, 666], [671, 651], [671, 672]]}

import types
import pytest

from pr_agent.git_providers.github_provider import GithubProvider
import pr_agent.git_providers.github_provider as gp_mod


class DummyRequester:
    def __init__(self, behavior):
        # behavior is a dict mapping method name to a callable(method, url, input) -> (headers, data)
        self.behavior = behavior
        self.calls = []

    def requestJsonAndCheck(self, method, url, input=None):
        self.calls.append((method, url, input))
        func = self.behavior.get(method)
        if func is None:
            raise RuntimeError(f"No behavior defined for method {method}")
        return func(method, url, input)


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def make_provider_with_requester(requester, repo="owner/repo"):
    # Create instance without calling __init__ to avoid heavy setup.
    prov = object.__new__(GithubProvider)
    # minimal attributes used by publish_file_comments
    prov.pr = types.SimpleNamespace(_requester=requester, url=f"https://api.github.com/repos/{repo}/pulls/1")
    prov.last_commit_id = types.SimpleNamespace(sha="deadbeefsha")
    prov.base_url = "https://api.github.com"
    prov.repo = repo
    prov.deployment_type = "app"  # default; tests may change
    prov.github_user_id = "someuser"
    prov.max_comment_chars = 65000
    return prov


def test_publish_file_comments_posts_new(monkeypatch):
    # Arrange: GET returns empty list, POST will be recorded
    def get_beh(method, url, input):
        return ({}, [])  # no existing comments

    def post_beh(method, url, input):
        return ({}, {"id": 123, "body": input})

    behavior = {"GET": get_beh, "POST": post_beh}
    requester = DummyRequester(behavior)
    provider = make_provider_with_requester(requester)

    # patch get_settings and logger used in module
    monkeypatch.setattr(gp_mod, "get_settings", lambda: {"GITHUB.APP_NAME": "TestApp"})
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp_mod, "get_logger", lambda: dummy_logger)

    file_comments = [{"path": "file.txt", "position": 10, "body": "a simple comment"}]

    # Act
    result = provider.publish_file_comments(file_comments)

    # Assert
    assert result is True
    # First call is GET to pr url /comments
    assert requester.calls[0][0] == "GET"
    assert requester.calls[0][1].endswith("/comments")
    # Second call is POST to pr comments
    assert any(c[0] == "POST" for c in requester.calls), "Expected a POST call to create new comment"
    post_calls = [c for c in requester.calls if c[0] == "POST"]
    assert len(post_calls) == 1
    method, url, sent_input = post_calls[0]
    assert url.endswith("/comments")
    # commit_id should have been set from last_commit_id.sha
    assert sent_input["commit_id"] == "deadbeefsha"
    # body should match original when short
    assert sent_input["body"] == "a simple comment"


def test_publish_file_comments_patches_existing_app_user(monkeypatch):
    # Arrange: GET returns one existing comment matching path and app user -> should PATCH
    existing_comment = {
        "id": 999,
        "subject_type": "file",
        "path": "file.txt",
        "user": {"login": "testapp-bot"}  # contains app name
    }

    def get_beh(method, url, input):
        return ({}, [existing_comment])

    def patch_beh(method, url, input):
        return ({}, {"id": existing_comment["id"], "body": input.get("body")})

    behavior = {"GET": get_beh, "PATCH": patch_beh}
    requester = DummyRequester(behavior)
    provider = make_provider_with_requester(requester)

    # ensure module get_settings returns an app name that matches existing_comment user
    monkeypatch.setattr(gp_mod, "get_settings", lambda: {"GITHUB.APP_NAME": "TestApp"})
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp_mod, "get_logger", lambda: dummy_logger)

    provider.deployment_type = "app"

    file_comments = [{"path": "file.txt", "position": 5, "body": "updated body"}]

    # Act
    result = provider.publish_file_comments(file_comments)

    # Assert
    assert result is True
    # should GET then PATCH, and not POST
    methods = [c[0] for c in requester.calls]
    assert methods[0] == "GET"
    assert "PATCH" in methods
    assert "POST" not in methods
    # Verify PATCH URL: should include repos/{repo}/pulls/comments/{id}
    patch_call = [c for c in requester.calls if c[0] == "PATCH"][0]
    _, patch_url, patch_input = patch_call
    assert f"/repos/{provider.repo}/pulls/comments/{existing_comment['id']}" in patch_url
    # body sent in PATCH should be the comment body (string) under input={"body": ...}
    assert isinstance(patch_input, dict)
    assert "body" in patch_input
    assert patch_input["body"] == "updated body"


def test_publish_file_comments_handles_exception_and_returns_false(monkeypatch):
    # Arrange: GET raises an exception
    def raising_get(method, url, input):
        raise RuntimeError("network failure")

    behavior = {"GET": raising_get}
    requester = DummyRequester(behavior)
    provider = make_provider_with_requester(requester)

    # patch get_settings and logger
    monkeypatch.setattr(gp_mod, "get_settings", lambda: {"GITHUB.APP_NAME": "TestApp"})
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp_mod, "get_logger", lambda: dummy_logger)

    file_comments = [{"path": "whatever", "position": 1, "body": "irrelevant"}]

    # Act
    result = provider.publish_file_comments(file_comments)

    # Assert: on exception should return False and logger.error should be called
    assert result is False
    assert dummy_logger.errors, "Expected logger.error to be called on exception"
    assert any("Failed to publish diffview file summary" in e for e in dummy_logger.errors)
