# file: pr_agent/git_providers/bitbucket_provider.py:352-378
# asked: {"lines": [357, 358, 359, 360, 361, 362, 363, 364, 365, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378], "branches": [[358, 359], [358, 378], [360, 358], [360, 361], [363, 364], [363, 367], [371, 372], [371, 374]]}
# gained: {"lines": [357, 358, 359, 360, 361, 362, 363, 364, 365, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378], "branches": [[358, 359], [358, 378], [360, 358], [360, 361], [363, 364], [363, 367], [371, 372], [371, 374]]}

import types
import pytest

from pr_agent.git_providers.bitbucket_provider import BitbucketProvider


class DummyPr:
    def __init__(self, comments):
        self._comments = comments

    def comments(self):
        return list(self._comments)


class FakeComment:
    def __init__(self, raw, raise_on_put=False):
        self.raw = raw
        self.put_calls = []
        self.raise_on_put = raise_on_put
        self._updated = None

    def put(self, none, data):
        if self.raise_on_put:
            raise RuntimeError("simulated put failure")
        self.put_calls.append((none, data))
        return {"result": "ok", "data": data}

    def _update_data(self, resp):
        self._updated = resp
        return resp


class DummyProvider:
    """
    We'll bind BitbucketProvider.publish_persistent_comment to an instance of this class.
    The instance supplies the attributes and methods used in the method under test.
    """
    def __init__(self, pr_comments):
        self.pr = DummyPr(pr_comments)
        self.published = []
        # provide deterministic urls
        self._latest = "http://example.com/commit/123"
        self._comment_url = "http://example.com/comment/1"

    def get_latest_commit_url(self):
        return self._latest

    def get_comment_url(self, comment):
        # pretend to use the comment to form a url
        return self._comment_url

    def publish_comment(self, msg):
        # collect published messages so tests can assert calls
        self.published.append(msg)


def bind_method_to_dummy():
    # get unbound function and bind it to a DummyProvider instance
    func = BitbucketProvider.publish_persistent_comment
    return func


def test_publish_persistent_comment_updates_header_and_posts_final_message():
    # initial header present in comment.raw, update_header True (default), final_update_message True (default)
    initial_header = "### Initial Header"
    pr_comment = f"{initial_header}\nSome body text"
    fake_comment = FakeComment(raw=f"This contains {initial_header} somewhere")
    dummy = DummyProvider([fake_comment])

    # bind method
    func = bind_method_to_dummy()
    bound = types.MethodType(func, dummy)

    # call method
    bound(pr_comment=pr_comment, initial_header=initial_header)

    # assert comment.put was called once with updated header inserted
    assert len(fake_comment.put_calls) == 1
    put_data = fake_comment.put_calls[0][1]
    assert "content" in put_data and "raw" in put_data["content"]
    updated_raw = put_data["content"]["raw"]
    # updated header should contain the initial header plus the '(Review updated until commit ...)' addition
    assert initial_header in updated_raw
    assert "(Review updated until commit" in updated_raw or "(review updated until commit" in updated_raw

    # assert final publish_comment was called with the expected message referencing the comment and commit url
    assert len(dummy.published) == 1
    assert f"updated to latest commit {dummy.get_latest_commit_url()}" in dummy.published[0]
    assert dummy.get_comment_url(fake_comment) in dummy.published[0]


def test_publish_persistent_comment_no_header_update_and_no_final_message():
    # initial header present, but update_header=False and final_update_message=False
    initial_header = "## MyHeader"
    pr_comment = f"{initial_header}\nKeep original"
    fake_comment = FakeComment(raw=f"prefix {initial_header} suffix")
    dummy = DummyProvider([fake_comment])

    func = bind_method_to_dummy()
    bound = types.MethodType(func, dummy)

    # call with update_header False and final_update_message False
    bound(pr_comment=pr_comment, initial_header=initial_header, update_header=False, final_update_message=False, name="customname")

    # put was called and raw content should be exactly the original pr_comment (no header change)
    assert len(fake_comment.put_calls) == 1
    put_data = fake_comment.put_calls[0][1]
    assert put_data["content"]["raw"] == pr_comment

    # no final publish_comment should have been called (method returned before fallback)
    assert dummy.published == []


def test_publish_persistent_comment_no_matching_comment_uses_fallback_publish():
    # No comment contains the initial header -> should call publish_comment(pr_comment) fallback
    initial_header = "### NotPresent"
    pr_comment = "some new message body"
    fake_comment = FakeComment(raw="unrelated comment body")
    dummy = DummyProvider([fake_comment])

    func = bind_method_to_dummy()
    bound = types.MethodType(func, dummy)

    bound(pr_comment=pr_comment, initial_header=initial_header)

    # No put calls since header not found
    assert fake_comment.put_calls == []

    # Fallback publish_comment should have been called with pr_comment
    assert len(dummy.published) == 1
    assert dummy.published[0] == pr_comment


def test_publish_persistent_comment_handles_exception_and_falls_back():
    # Simulate exception during update (comment.put raises). Should be caught and fallback publish_comment(pr_comment) executed.
    initial_header = "## Header"
    pr_comment = "fallback message"
    # create a comment that will raise when put is called
    bad_comment = FakeComment(raw=f"contains {initial_header}", raise_on_put=True)
    dummy = DummyProvider([bad_comment])

    func = bind_method_to_dummy()
    bound = types.MethodType(func, dummy)

    # Should not raise despite the internal put raising
    bound(pr_comment=pr_comment, initial_header=initial_header)

    # Because put raised, no successful put recorded
    assert bad_comment.put_calls == []

    # Fallback publish_comment should have been called with pr_comment
    assert dummy.published == [pr_comment]
