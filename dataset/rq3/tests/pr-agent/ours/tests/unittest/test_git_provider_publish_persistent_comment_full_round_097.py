import types
import pytest
from pr_agent.git_providers import git_provider as gp
from pr_agent.git_providers.git_provider import GitProvider


class FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.exception_calls = []

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exception_calls.append((args, kwargs))


class FakeComment:
    def __init__(self, body, id="c1"):
        self.body = body
        self.id = id


class FakeSelf:
    def __init__(self,
                 issue_comments=None,
                 latest_commit_url="commit123",
                 comment_url="http://example/comment/1",
                 publish_return="published",
                 raise_on_get_comments=False):
        # issue_comments can be a list or callable or exception flag
        self._issue_comments = issue_comments if issue_comments is not None else []
        self._latest_commit_url = latest_commit_url
        self._comment_url = comment_url
        self._publish_return = publish_return
        self._raise_on_get_comments = raise_on_get_comments

        # recorders
        self.edits = []
        self.publishes = []

    def get_issue_comments(self):
        if self._raise_on_get_comments:
            raise Exception("boom")
        # allow a callable for dynamic behavior
        if callable(self._issue_comments):
            return self._issue_comments()
        return list(self._issue_comments)

    def get_latest_commit_url(self):
        return self._latest_commit_url

    def get_comment_url(self, comment):
        return self._comment_url

    def edit_comment(self, comment, body):
        self.edits.append((comment, body))

    def publish_comment(self, pr_comment):
        self.publishes.append(pr_comment)
        return self._publish_return


def call_publish(fn_self, pr_comment, initial_header, update_header=True, name="review", final_update_message=True):
    # call the original function implementation by binding the function from the class
    return GitProvider.publish_persistent_comment_full(fn_self, pr_comment, initial_header, update_header, name, final_update_message)


def test_no_prev_comments_calls_publish_round_097(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    fs = FakeSelf(issue_comments=[], publish_return="PUBLISH_OK")
    res = call_publish(fs, pr_comment="NoHeader body", initial_header="HEADER_NOT_PRESENT")

    # should have called publish_comment with the original pr_comment and returned its value
    assert fs.publishes == ["NoHeader body"]
    assert res == "PUBLISH_OK"
    # nothing should have been edited
    assert fs.edits == []
    # logger.exception should not have been called
    assert fake_logger.exception_calls == []


def test_non_matching_prev_comments_calls_publish_round_097(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    c1 = FakeComment("SOME OTHER HEADER\ncontent")
    fs = FakeSelf(issue_comments=[c1], publish_return="PUBLISH_NONMATCH")

    res = call_publish(fs, pr_comment="No match here", initial_header="HEADER_NOT_PRESENT")

    # loop runs but no comment.body startswith initial_header, so publish called with original
    assert fs.publishes == ["No match here"]
    assert res == "PUBLISH_NONMATCH"
    assert fs.edits == []


def test_existing_comment_update_and_final_message_round_097(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    initial_header = "INITIAL_HEADER"
    # pr_comment contains the initial header so replacement will occur
    pr_comment = "INITIAL_HEADER\nthis is body"
    comment = FakeComment(initial_header + "\nold stuff", id="c42")

    fs = FakeSelf(issue_comments=[comment], latest_commit_url="sha-abc", comment_url="http://c/42", publish_return="PUBLISHED_MSG")

    res = call_publish(fs, pr_comment=pr_comment, initial_header=initial_header, update_header=True, name="review", final_update_message=True)

    # edit_comment should have been called once with the updated header replaced into pr_comment
    assert len(fs.edits) == 1
    edited_comment, edited_body = fs.edits[0]
    assert edited_comment is comment

    expected_updated_header = f"{initial_header}\n\n#### (Review updated until commit sha-abc)\n"
    assert expected_updated_header in edited_body
    # publish_comment should have been called with the final update message and returned value propagated
    expected_publish_arg = f"**[Persistent review](http://c/42)** updated to latest commit sha-abc"
    assert fs.publishes == [expected_publish_arg]
    assert res == "PUBLISHED_MSG"
    # logger.info should have been called at least once
    assert fake_logger.info_calls, "expected logger.info to be called for update path"


def test_existing_comment_no_update_final_false_returns_comment_round_097(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    initial_header = "HEAD"
    pr_comment = "HEAD\nbody keeps same"
    comment = FakeComment(initial_header + "\nprevious")

    fs = FakeSelf(issue_comments=[comment], publish_return="SHOULD_NOT_BE_USED")

    # update_header False and final_update_message False -> should edit with original pr_comment and return the comment object
    res = call_publish(fs, pr_comment=pr_comment, initial_header=initial_header, update_header=False, name="review", final_update_message=False)

    # edit called with original pr_comment (no header replacement)
    assert len(fs.edits) == 1
    edited_comment, edited_body = fs.edits[0]
    assert edited_comment is comment
    assert edited_body == pr_comment

    # since final_update_message is False, function should return the comment object
    assert res is comment
    # publish_comment should not have been called in this branch
    assert fs.publishes == []


def test_get_issue_comments_raises_logs_and_publishes_round_097(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    fs = FakeSelf(raise_on_get_comments=True, publish_return="RECOVERED")

    res = call_publish(fs, pr_comment="recover body", initial_header="anything")

    # When get_issue_comments raises, exception should be logged and publish_comment called with original pr_comment
    assert fs.publishes == ["recover body"]
    assert res == "RECOVERED"

    # check that an exception was recorded containing the expected prefix and the underlying error message
    assert fake_logger.exception_calls, "expected logger.exception to be called when get_issue_comments raises"
    args, kwargs = fake_logger.exception_calls[0]
    # first positional arg should be the composed message
    logged_message = args[0] if args else ""
    assert "Failed to update persistent review" in logged_message
    assert "boom" in logged_message
