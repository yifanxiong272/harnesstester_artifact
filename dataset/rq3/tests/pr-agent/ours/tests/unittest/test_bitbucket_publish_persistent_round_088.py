import importlib
import types
import pytest

bb_mod = importlib.import_module("pr_agent.git_providers.bitbucket_provider")
BitbucketProvider = bb_mod.BitbucketProvider

class DummyComment:
    def __init__(self, raw, put_ret=None, update_ret=None):
        self.raw = raw
        self._put_calls = []
        self._update_calls = []
        self._put_ret = put_ret if put_ret is not None else {"ok": True}
        self._update_ret = update_ret if update_ret is not None else {"updated": True}

    def put(self, arg, data=None):
        # mimic the signature used in the code: comment.put(None, data=d)
        self._put_calls.append((arg, data))
        return self._put_ret

    def _update_data(self, resp):
        self._update_calls.append(resp)
        return self._update_ret


def make_provider_instance():
    # create instance without running __init__ and attach required attributes
    prov = BitbucketProvider.__new__(BitbucketProvider)
    return prov


def setup_logger(monkeypatch, logger_msgs):
    # get_logger() should return an object with info and exception methods
    logger = types.SimpleNamespace(
        info=lambda *a, **k: logger_msgs.append(("info", a)),
        exception=lambda *a, **k: logger_msgs.append(("exception", a)),
    )
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)
    return logger


def test_update_header_and_final_message_round_088(monkeypatch):
    """
    Verify that when a persistent comment containing the initial header is found,
    and update_header=True and final_update_message=True, the comment is updated
    with the updated header and a final publish_comment message is emitted.
    """
    logger_msgs = []
    setup_logger(monkeypatch, logger_msgs)

    prov = make_provider_instance()

    # stubbed methods and state
    prov.get_latest_commit_url = lambda: "commit-url"
    prov.get_comment_url = lambda comment: "comment-url"

    published = []
    prov.publish_comment = lambda msg: published.append(msg)

    # comment contains the initial header
    initial_header = "Initial Header"
    pr_comment = "Initial Header\nSome body"
    comment = DummyComment(raw="prefix Initial Header suffix")

    prov.pr = types.SimpleNamespace(comments=lambda: [comment])

    # patch module-level get_logger already done; call method
    prov.publish_persistent_comment(pr_comment, initial_header, update_header=True, name="review", final_update_message=True)

    # Assert that the comment.put was called with the updated content
    assert comment._put_calls, "comment.put was not called"
    arg, data = comment._put_calls[0]
    assert arg is None
    expected_updated_header = f"{initial_header}\n\n#### (Review updated until commit commit-url)\n"
    expected_pr_comment_updated = pr_comment.replace(initial_header, expected_updated_header)
    assert data == {"content": {"raw": expected_pr_comment_updated}}

    # Assert that publish_comment was called with the final update message
    assert published, "final publish_comment was not called"
    assert published[0] == f"**[Persistent review](comment-url)** updated to latest commit commit-url"


def test_update_header_no_final_message_round_088(monkeypatch):
    """
    When update_header=False and final_update_message=False, the comment is
    updated without emitting the final publish message.
    """
    logger_msgs = []
    setup_logger(monkeypatch, logger_msgs)

    prov = make_provider_instance()
    prov.get_latest_commit_url = lambda: "commit-2"
    prov.get_comment_url = lambda comment: "comment-url-2"

    published = []
    prov.publish_comment = lambda msg: published.append(msg)

    initial_header = "Hdr"
    pr_comment = "Hdr\ncontent"
    comment = DummyComment(raw="Hdr present")
    prov.pr = types.SimpleNamespace(comments=lambda: [comment])

    prov.publish_persistent_comment(pr_comment, initial_header, update_header=False, name="review", final_update_message=False)

    # comment.put should have been called with the original pr_comment
    assert comment._put_calls, "comment.put was not called"
    _, data = comment._put_calls[0]
    assert data == {"content": {"raw": pr_comment}}

    # No final publish message should have been emitted
    assert published == [], "publish_comment should not have been called for final update"


def test_no_matching_comments_publishes_direct_round_088(monkeypatch):
    """
    If no existing comments contain the initial header, the method should fall
    through and publish the provided pr_comment directly.
    """
    logger_msgs = []
    setup_logger(monkeypatch, logger_msgs)

    prov = make_provider_instance()
    published = []
    prov.publish_comment = lambda msg: published.append(msg)

    initial_header = "NotPresent"
    pr_comment = "A new comment body"
    # comment.raw does not contain the initial header
    comment = DummyComment(raw="other content")
    prov.pr = types.SimpleNamespace(comments=lambda: [comment])

    prov.publish_persistent_comment(pr_comment, initial_header, update_header=True, name="review", final_update_message=True)

    # Should publish the original pr_comment because no comment matched
    assert published == [pr_comment]


def test_exception_during_processing_round_088(monkeypatch):
    """
    If an exception occurs inside the try block, it should be logged and the
    method should still attempt to publish the provided pr_comment afterwards.
    """
    logger_msgs = []
    logger = setup_logger(monkeypatch, logger_msgs)

    prov = make_provider_instance()
    published = []
    prov.publish_comment = lambda msg: published.append(msg)

    # make comments() raise to trigger the except branch
    def raising_comments():
        raise RuntimeError("boom")

    prov.pr = types.SimpleNamespace(comments=raising_comments)

    pr_comment = "Fallback comment"
    prov.publish_persistent_comment(pr_comment, "hdr", update_header=True, name="review", final_update_message=True)

    # Exception should have been logged, and publish_comment should be called
    assert any(entry[0] == "exception" for entry in logger_msgs), "exception not logged"
    assert published == [pr_comment]
