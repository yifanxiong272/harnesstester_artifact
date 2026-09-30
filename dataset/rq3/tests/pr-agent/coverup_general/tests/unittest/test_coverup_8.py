# file: pr_agent/servers/github_polling.py:76-141
# asked: {"lines": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 106, 107, 109, 110, 112, 113, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 135, 137, 138, 139, 140, 141], "branches": [[78, 79], [78, 137], [79, 80], [79, 137], [82, 83], [82, 85], [88, 89], [88, 137], [90, 91], [90, 96], [91, 92], [91, 95], [96, 97], [96, 100], [97, 98], [97, 100], [101, 102], [101, 105], [105, 106], [105, 109], [112, 113], [112, 116], [120, 121], [120, 133], [121, 122], [121, 124], [122, 123], [122, 124], [125, 126], [125, 127], [127, 120], [127, 128]]}
# gained: {"lines": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 106, 107, 112, 116, 117, 118, 119, 120, 121, 122, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 135, 138, 139, 140, 141], "branches": [[78, 79], [79, 80], [82, 83], [82, 85], [88, 89], [90, 91], [91, 92], [91, 95], [96, 97], [97, 98], [97, 100], [101, 102], [101, 105], [105, 106], [112, 116], [120, 121], [120, 133], [121, 122], [122, 124], [125, 126], [125, 127], [127, 120], [127, 128]]}

import asyncio
import types
import pytest

from pr_agent.servers import github_polling
from pr_agent.servers.github_polling import is_valid_notification


class DummyAsyncResponse:
    def __init__(self, status=200, json_data=None):
        self.status = status
        self._json_data = json_data if json_data is not None else {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json_data


class DummySession:
    def __init__(self, response_cm):
        self._response_cm = response_cm

    def get(self, url, headers=None):
        # return an async context manager
        return self._response_cm


class DummyRequestsResponse:
    def __init__(self, comments):
        self._comments = comments

    def json(self):
        return self._comments


def make_notification(latest_comment):
    return {
        "reason": "mention",
        "subject": {
            "type": "PullRequest",
            "url": "https://api.github.com/repos/org/repo/pulls/1",
            "latest_comment_url": latest_comment,
        },
    }


@pytest.mark.asyncio
async def test_no_latest_comment_returns_false():
    notification = make_notification(latest_comment=None)
    handled = set()
    session = DummySession(DummyAsyncResponse(status=200, json_data={"id": 1, "body": "hi"}))
    result = await is_valid_notification(notification, headers={"a": "b"}, handled_ids=handled, session=session, user_id="me")
    assert result == (False, handled)


@pytest.mark.asyncio
async def test_comment_id_in_handled_returns_false(monkeypatch):
    # latest comment exists and returns id that's already handled
    notification = make_notification(latest_comment="https://api.github.com/comment/5")
    handled = {5}
    resp = DummyAsyncResponse(status=200, json_data={"id": 5, "body": "hello"})
    session = DummySession(resp)
    # Ensure requests.get is never called in this path, but safe to stub it
    monkeypatch.setattr(github_polling, "requests", types.SimpleNamespace(get=lambda *a, **k: DummyRequestsResponse([])))
    result = await is_valid_notification(notification, headers={}, handled_ids=handled, session=session, user_id="me")
    assert result == (False, handled)
    # handled should remain unchanged
    assert handled == {5}


@pytest.mark.asyncio
async def test_prev_comments_found_when_latest_by_self_or_no_body(monkeypatch):
    # latest comment has id not in handled_ids, user == user_id (so skip), then previous comments contain tag
    latest_url = "https://api.github.com/comment/6"
    notification = make_notification(latest_comment=latest_url)
    handled = set()
    latest_comment = {"id": 6, "user": {"login": "me"}, "body": ""}  # user == user_id triggers check_prev_comments
    resp = DummyAsyncResponse(status=200, json_data=latest_comment)
    session = DummySession(resp)

    # previous comments: one older comment contains the user tag
    prev_comments = [
        {"id": 1, "user": {"login": "other"}, "body": "some text"},
        {"id": 2, "user": {"login": "other2"}, "body": "hey @me please look"},
        {"id": 3, "user": {"login": "other3"}, "body": None},
    ]
    # requests.get should return an object whose .json() returns the list
    def fake_requests_get(url, headers=None):
        return DummyRequestsResponse(prev_comments)

    monkeypatch.setattr(github_polling, "requests", types.SimpleNamespace(get=fake_requests_get))

    result = await is_valid_notification(notification, headers={}, handled_ids=handled, session=session, user_id="me")
    # should return a 6-tuple indicating valid with the matching previous comment (id 2)
    assert isinstance(result, tuple)
    assert result[0] is True
    returned_handled = result[1]
    returned_comment = result[2]
    returned_body = result[3]
    returned_pr_url = result[4]
    returned_user_tag = result[5]

    assert 6 in returned_handled  # latest comment id should have been added
    assert returned_comment["id"] == 2
    assert "@me" in returned_body
    assert returned_pr_url == "https://api.github.com/repos/org/repo/pulls/1"
    assert returned_user_tag == "@me"


@pytest.mark.asyncio
async def test_prev_comments_no_tag_returns_false_and_logs_warning(monkeypatch):
    # latest comment has a body without the user tag; previous comments also don't contain tag
    latest_url = "https://api.github.com/comment/7"
    notification = make_notification(latest_comment=latest_url)
    handled = set()
    latest_comment = {"id": 7, "user": {"login": "other"}, "body": "hello world"}  # no tag -> check_prev_comments True
    resp = DummyAsyncResponse(status=200, json_data=latest_comment)
    session = DummySession(resp)

    prev_comments = [
        {"id": 10, "user": {"login": "other"}, "body": "no mention here"},
        {"id": 11, "user": {"login": "other2"}, "body": ""},
    ]

    def fake_requests_get(url, headers=None):
        return DummyRequestsResponse(prev_comments)

    monkeypatch.setattr(github_polling, "requests", types.SimpleNamespace(get=fake_requests_get))

    result = await is_valid_notification(notification, headers={}, handled_ids=handled, session=session, user_id="me")
    # should return False and handled should contain the latest id (7) because it was added before scanning prev comments
    assert result == (False, handled)
    assert 7 in handled


@pytest.mark.asyncio
async def test_exception_in_processing_returns_false(monkeypatch):
    # simulate session.get raising an exception to trigger the except block
    latest_url = "https://api.github.com/comment/8"
    notification = make_notification(latest_comment=latest_url)
    handled = set()

    class RaisingSession:
        def get(self, url, headers=None):
            raise RuntimeError("network error")

    session = RaisingSession()
    # stub requests.get to ensure it's not used
    monkeypatch.setattr(github_polling, "requests", types.SimpleNamespace(get=lambda *a, **k: DummyRequestsResponse([])))

    result = await is_valid_notification(notification, headers={}, handled_ids=handled, session=session, user_id="me")
    assert result == (False, handled)
