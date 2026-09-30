import importlib
import types
import pytest

from openhands.resolver.interfaces.azure_devops import AzureDevOpsIssueHandler


def make_handler_without_init():
    """Create an instance without calling __init__ so tests don't depend on constructor side-effects."""
    handler = object.__new__(AzureDevOpsIssueHandler)
    # Provide the minimal attributes used by reply_to_comment
    handler.repo_api_url = "https://dev.azure.com/fakeorg/_apis/git/repositories/fakeRepo"
    handler.get_headers = lambda: {"Authorization": "Basic FAKE"}
    return handler


def test_reply_to_comment_success_round_080(monkeypatch):
    """When the comment exists in the thread, post is called with the expected URL and JSON."""
    module = importlib.import_module("openhands.resolver.interfaces.azure_devops")

    # Prepare threads with a matching comment id '7'
    threads = [
        {
            "id": 555,
            "comments": [{"id": 1}, {"id": 2}],
        },
        {
            "id": 42,
            "comments": [{"id": 7}, {"id": 8}],
        },
    ]

    captured = {"get_raise_called": False, "post_raise_called": False}

    class DummyGetResponse:
        def __init__(self, threads):
            self._threads = threads

        def json(self):
            return {"value": self._threads}

        def raise_for_status(self):
            captured["get_raise_called"] = True

    class DummyPostResponse:
        def raise_for_status(self):
            captured["post_raise_called"] = True

    def fake_get(url, headers=None):
        # Ensure the URL uses the handler's repo_api_url and pr number
        captured["get_url"] = url
        captured["get_headers"] = headers
        return DummyGetResponse(threads)

    def fake_post(url, headers=None, json=None):
        captured["post_url"] = url
        captured["post_headers"] = headers
        captured["post_json"] = json
        return DummyPostResponse()

    # Patch the httpx functions used in the module under test
    monkeypatch.setattr(module.httpx, "get", fake_get)
    monkeypatch.setattr(module.httpx, "post", fake_post)

    handler = make_handler_without_init()

    pr_number = 123
    comment_id = "7"
    reply_text = "Thanks for the feedback"

    # Call the method under test
    handler.reply_to_comment(pr_number=pr_number, comment_id=comment_id, reply=reply_text)

    # Validate get was called and raise_for_status executed
    assert captured["get_url"].endswith(f"/pullRequests/{pr_number}/threads?api-version=7.1")
    assert captured["get_raise_called"] is True

    # Validate post was called with the thread id found (42) and correct JSON payload
    expected_post_url = f"{handler.repo_api_url}/pullRequests/{pr_number}/threads/42/comments?api-version=7.1"
    assert captured["post_url"] == expected_post_url
    assert captured["post_headers"] == handler.get_headers()
    assert captured["post_json"] == {"content": reply_text, "parentCommentId": int(comment_id)}
    assert captured["post_raise_called"] is True


def test_reply_to_comment_not_found_raises_round_080(monkeypatch):
    """When the comment id is not present in any thread, a ValueError is raised and post is not called."""
    module = importlib.import_module("openhands.resolver.interfaces.azure_devops")

    # Threads that do not contain the comment id '999'
    threads = [
        {"id": 1, "comments": [{"id": 10}, {"id": 11}]},
        {"id": 2, "comments": [{"id": 20}]},
    ]

    class DummyGetResponse:
        def __init__(self, threads):
            self._threads = threads

        def json(self):
            return {"value": self._threads}

        def raise_for_status(self):
            # No-op but markable if needed
            pass

    def fake_get(url, headers=None):
        return DummyGetResponse(threads)

    # If post is called in this scenario, fail the test explicitly
    def fake_post(url, headers=None, json=None):
        pytest.fail("httpx.post should not be called when the comment is not found")

    monkeypatch.setattr(module.httpx, "get", fake_get)
    monkeypatch.setattr(module.httpx, "post", fake_post)

    handler = make_handler_without_init()

    pr_number = 7
    missing_comment_id = "999"

    with pytest.raises(ValueError) as excinfo:
        handler.reply_to_comment(pr_number=pr_number, comment_id=missing_comment_id, reply="nope")

    # Ensure the error message mentions the comment id and PR number
    assert str(missing_comment_id) in str(excinfo.value)
    assert str(pr_number) in str(excinfo.value)
