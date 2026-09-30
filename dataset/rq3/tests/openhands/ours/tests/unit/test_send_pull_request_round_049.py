import json
import types
import pytest

import openhands.resolver.send_pull_request as spr
from openhands.integrations.service_types import ProviderType


class _MockServiceContextHandler:
    def __init__(self, pull_url="http://example/pr", authorize_url="ssh://auth/"):
        self._pull_url = pull_url
        self._authorize_url = authorize_url
        self.sent_comments = []
        self.replies = []

    def get_authorize_url(self):
        return self._authorize_url

    def get_pull_url(self, number):
        # include number in returned url for easier assertions
        return f"{self._pull_url}/{number}"

    def send_comment_msg(self, number, msg):
        self.sent_comments.append((number, msg))

    def reply_to_comment(self, number, comment_id, msg):
        self.replies.append((number, comment_id, msg))


class _DummyHandlerClass:
    # Accept anything in constructor to avoid accidental import/construct errors
    def __init__(self, *a, **k):
        pass


def _patch_handlers_and_servicecontext(monkeypatch, mock_handler):
    # Ensure none of the concrete handler classes raise on construction
    monkeypatch.setattr(spr, "GithubIssueHandler", _DummyHandlerClass, raising=False)
    monkeypatch.setattr(spr, "GitlabIssueHandler", _DummyHandlerClass, raising=False)
    monkeypatch.setattr(spr, "AzureDevOpsIssueHandler", _DummyHandlerClass, raising=False)
    monkeypatch.setattr(spr, "BitbucketIssueHandler", _DummyHandlerClass, raising=False)
    monkeypatch.setattr(spr, "BitbucketDCIssueHandler", _DummyHandlerClass, raising=False)
    monkeypatch.setattr(spr, "ForgejoIssueHandler", _DummyHandlerClass, raising=False)

    # Patch ServiceContextIssue to return our mock handler regardless of args
    monkeypatch.setattr(
        spr, "ServiceContextIssue", lambda *_args, **_kwargs: mock_handler, raising=False
    )


def _make_issue(owner, repo, head_branch, number, thread_ids=None):
    return types.SimpleNamespace(owner=owner, repo=repo, head_branch=head_branch, number=number, thread_ids=(thread_ids or []))


def test_push_failure_raises_runtime_error_round_049(monkeypatch):
    """If pushing fails (subprocess.returncode != 0) the function should raise RuntimeError."""
    mock_handler = _MockServiceContextHandler(pull_url="http://pr")
    _patch_handlers_and_servicecontext(monkeypatch, mock_handler)

    # Simulate a failing git push
    monkeypatch.setattr(
        spr, "subprocess", types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=1, stderr="push failed")), raising=False
    )

    issue = _make_issue("owner", "repo", "branch", 1, thread_ids=[])

    with pytest.raises(RuntimeError):
        spr.update_existing_pull_request(
            issue=issue,
            token="tok",
            username=None,
            platform=ProviderType.GITHUB,
            patch_dir="/tmp/patch",
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )


def test_azure_devops_additional_message_and_thread_replies_round_049(monkeypatch):
    """Azure DevOps branch: owner split into organization/project and replies/comments are sent for JSON additional_message."""
    # prepare handler that records calls
    mock_handler = _MockServiceContextHandler(pull_url="http://pr")
    _patch_handlers_and_servicecontext(monkeypatch, mock_handler)

    # Simulate successful push
    monkeypatch.setattr(
        spr,
        "subprocess",
        types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=0, stderr="")),
        raising=False,
    )

    # owner is organization/project for Azure DevOps
    issue = _make_issue("org/project", "repo", "branch-x", 2, thread_ids=[101, 102])

    additional_message = json.dumps(["exA", "exB"])  # valid JSON list

    pr_url = spr.update_existing_pull_request(
        issue=issue,
        token="tok",
        username=None,
        platform=ProviderType.AZURE_DEVOPS,
        patch_dir="/tmp/patch",
        llm_config=None,
        comment_message=None,
        additional_message=additional_message,
        base_domain=None,
    )

    # The mocked get_pull_url returns url including the issue.number
    assert pr_url.endswith("/2")

    # A composed comment message with both explanations should have been sent once
    assert len(mock_handler.sent_comments) >= 1
    sent_number, sent_msg = mock_handler.sent_comments[0]
    assert sent_number == 2
    assert "- exA" in sent_msg and "- exB" in sent_msg

    # Replies to threads should be sent for each explanation in order
    assert mock_handler.replies == [(2, 101, "exA"), (2, 102, "exB")]


def test_additional_message_json_decode_sets_comment_round_049(monkeypatch):
    """If additional_message is invalid JSON, the comment_message fallback should be posted."""
    mock_handler = _MockServiceContextHandler(pull_url="http://pr")
    _patch_handlers_and_servicecontext(monkeypatch, mock_handler)

    # Simulate successful push
    monkeypatch.setattr(
        spr,
        "subprocess",
        types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=0, stderr="")),
        raising=False,
    )

    issue = _make_issue("owner", "repo", "branch", 3, thread_ids=[])

    bad_additional = "this is not json"

    pr_url = spr.update_existing_pull_request(
        issue=issue,
        token="tok",
        username=None,
        platform=ProviderType.GITHUB,
        patch_dir="/tmp/patch",
        llm_config=None,
        comment_message=None,
        additional_message=bad_additional,
        base_domain=None,
    )

    # Should still return pull url
    assert pr_url.endswith("/3")

    # Because JSON parsing for additional_message failed in the initial block,
    # comment_message should be set to the fallback explanatory string and posted
    assert any(bad_additional in msg for (_n, msg) in mock_handler.sent_comments)


def test_reply_threads_json_decode_calls_send_msg_round_049(monkeypatch):
    """When replying to threads and additional_message is invalid JSON, send_comment_msg should be called with error description."""
    mock_handler = _MockServiceContextHandler(pull_url="http://pr")
    _patch_handlers_and_servicecontext(monkeypatch, mock_handler)

    # Simulate successful push
    monkeypatch.setattr(
        spr,
        "subprocess",
        types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=0, stderr="")),
        raising=False,
    )

    # Provide thread ids so the reply-to-threads branch is executed
    issue = _make_issue("owner", "repo", "branch", 4, thread_ids=[201])

    bad_additional = "not json"

    pr_url = spr.update_existing_pull_request(
        issue=issue,
        token="tok",
        username=None,
        platform=ProviderType.GITHUB,
        patch_dir="/tmp/patch",
        llm_config=None,
        comment_message=None,
        additional_message=bad_additional,
        base_domain=None,
    )

    assert pr_url.endswith("/4")

    # First the general fallback comment (about failing to parse/summarize) should be sent
    assert any("failed to parse" in msg for (_n, msg) in mock_handler.sent_comments)

    # Then the reply-to-threads JSONDecodeError branch should trigger an additional send_comment_msg
    assert any(("Error occurred when replying to threads" in msg) or ("Error occurred when replying to threads" in msg)
               for (_n, msg) in mock_handler.sent_comments)
