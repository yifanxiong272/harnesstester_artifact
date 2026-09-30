import types
import pytest

from openhands.resolver.interfaces import azure_devops
from openhands.resolver.interfaces.azure_devops import AzureDevOpsIssueHandler


class DummyResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code
        self.raise_called = False

    def json(self):
        return self._json

    def raise_for_status(self):
        # mimic httpx.Response.raise_for_status: do nothing for <400, raise for >=400
        self.raise_called = True
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def make_handler_with_repo_url():
    # Instantiate with dummy args; we'll override repo_api_url and get_headers for determinism
    h = AzureDevOpsIssueHandler(token="tok", organization="org", project="proj", repository="repo")
    # force a stable repo_api_url used by the implementation
    h.repo_api_url = "https://example.org/repos/repo1"
    # ensure deterministic headers
    h.get_headers = lambda: {"Authorization": "Bearer deterministic-token"}
    return h


def test_reply_to_comment_success_round_080(monkeypatch):
    """When the comment exists in a thread, reply_to_comment should POST to the correct URL

    This covers the loops that find the thread and triggers the POST path.
    """
    handler = make_handler_with_repo_url()

    pr_number = 123
    comment_id = "55"  # note: code compares str(comment.get('id')) == comment_id
    reply_text = "Thanks for your comment"

    # Prepare threads response: one thread contains a comment with id=55 (int)
    threads_payload = {"value": [
        {"id": "T1", "comments": [{"id": 55, "text": "orig"}]}
    ]}

    # Patch httpx.get to return the threads
    def fake_get(url, headers=None):
        # assert threads URL formation
        expected = f"{handler.repo_api_url}/pullRequests/{pr_number}/threads?api-version=7.1"
        assert url == expected
        # ensure headers come from handler.get_headers()
        assert headers == handler.get_headers()
        return DummyResponse(json_data=threads_payload)

    post_calls = []

    def fake_post(url, headers=None, json=None):
        post_calls.append({"url": url, "headers": headers, "json": json})
        return DummyResponse(json_data={"id": 999}, status_code=200)

    # Patch the httpx functions used by the module under test
    monkeypatch.setattr(azure_devops, "httpx", azure_devops.httpx)
    monkeypatch.setattr(azure_devops.httpx, "get", fake_get)
    monkeypatch.setattr(azure_devops.httpx, "post", fake_post)

    # Call the function under test
    handler.reply_to_comment(pr_number=pr_number, comment_id=comment_id, reply=reply_text)

    # Assert that a single POST was performed with the expected URL and payload
    assert len(post_calls) == 1
    call = post_calls[0]
    expected_post_url = f"{handler.repo_api_url}/pullRequests/{pr_number}/threads/T1/comments?api-version=7.1"
    assert call["url"] == expected_post_url
    # headers should be exactly what get_headers returned
    assert call["headers"] == handler.get_headers()
    # JSON payload content and parentCommentId must match expectations
    assert call["json"]["content"] == reply_text
    assert call["json"]["parentCommentId"] == int(comment_id)


def test_reply_to_comment_not_found_round_080(monkeypatch):
    """When the comment id is not present in any thread, a ValueError is raised.

    This covers the branch that raises when thread_id is not found.
    """
    handler = make_handler_with_repo_url()

    pr_number = 42
    missing_comment_id = "999"

    # Threads exist but none contain the target comment id
    threads_payload = {"value": [
        {"id": "T-A", "comments": [{"id": 1}, {"id": 2}]},
        {"id": "T-B", "comments": [{"id": 3}, {"id": 4}]}
    ]}

    def fake_get(url, headers=None):
        expected = f"{handler.repo_api_url}/pullRequests/{pr_number}/threads?api-version=7.1"
        assert url == expected
        assert headers == handler.get_headers()
        return DummyResponse(json_data=threads_payload)

    # Patch httpx.get; post should not be called in this scenario.
    post_called = {"count": 0}

    def fake_post(url, headers=None, json=None):
        post_called["count"] += 1
        return DummyResponse()

    monkeypatch.setattr(azure_devops, "httpx", azure_devops.httpx)
    monkeypatch.setattr(azure_devops.httpx, "get", fake_get)
    monkeypatch.setattr(azure_devops.httpx, "post", fake_post)

    with pytest.raises(ValueError) as exc:
        handler.reply_to_comment(pr_number=pr_number, comment_id=missing_comment_id, reply="nope")

    # Verify the error message contains the comment id and pr number
    assert f"Comment ID {missing_comment_id} not found in PR {pr_number}" in str(exc.value)
    # Ensure post was never called
    assert post_called["count"] == 0
