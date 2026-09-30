import builtins
import io
import json
import types
import pytest
from types import SimpleNamespace

import openhands.resolver.send_pull_request as sp
from openhands.integrations.service_types import ProviderType


class DummyHandler:
    def __init__(self):
        self.sent_comments = []
        self.replies = []

    def get_authorize_url(self):
        return "https://fake-authorize/"

    def get_pull_url(self, number):
        return f"https://fake-pr/{number}"

    def send_comment_msg(self, number, msg):
        self.sent_comments.append((number, msg))

    def reply_to_comment(self, number, comment_id, msg):
        self.replies.append((number, comment_id, msg))


class DummyCompleted:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


class DummyLLM:
    def __init__(self, config, service_id=None):
        self.config = config
        self.service_id = service_id

    def completion(self, messages=None):
        # Return an object with the shape used by the code under test
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="LLM summarized output"))])


class DummyTemplate:
    def __init__(self, _s):
        self._s = _s

    def render(self, **kwargs):
        # The send_pull_request code passes comment_message; return that so LLM receives it
        return kwargs.get("comment_message", "")


@pytest.fixture(autouse=True)
def patch_handlers_and_utils(monkeypatch):
    """Patch external handlers and tools to deterministic, in-memory fakes.

    This fixture patches:
    - the various handler classes to simple factories so they are not constructed
      (their instances are ignored because ServiceContextIssue is patched below)
    - ServiceContextIssue to return a test-controlled DummyHandler instance
    - the LLM implementation to a deterministic DummyLLM
    - jinja2.Template to a DummyTemplate used for prompt rendering
    - ensures subprocess.run can be overridden per-test by monkeypatching
    """
    # Replace handler classes so their construction is a no-op object (won't be used)
    for name in (
        "GithubIssueHandler",
        "GitlabIssueHandler",
        "AzureDevOpsIssueHandler",
        "BitbucketIssueHandler",
        "BitbucketDCIssueHandler",
        "ForgejoIssueHandler",
    ):
        if hasattr(sp, name):
            monkeypatch.setattr(sp, name, lambda *a, **k: object())

    # Patch LLM and Template to deterministic fakes
    monkeypatch.setattr(sp, "LLM", DummyLLM)
    monkeypatch.setattr(sp.jinja2, "Template", DummyTemplate)

    # Keep original builtins.open around so tests can selectively forward other opens
    original_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        # If the file open is the summary template the code expects, return a simple file-like
        if str(path).endswith("pr-changes-summary.jinja"):
            return io.StringIO("{{ comment_message }}")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    # Allow subprocess.run to be patched by individual tests; default to a success
    monkeypatch.setattr(sp, "subprocess", sp.subprocess)

    yield


def test_push_failure_raises_runtime_error_round_049(monkeypatch):
    """Simulate a failed git push (non-zero returncode) and assert RuntimeError is raised.

    This covers the error branch when subprocess.run returns a non-zero returncode
    (lines around 548-551 in the targeted segment).
    """
    # Prepare a dummy handler instance and patch ServiceContextIssue to return it
    handler = DummyHandler()
    monkeypatch.setattr(sp, "ServiceContextIssue", lambda *_: handler)

    # Ensure any handler constructors used in argument evaluation won't error
    monkeypatch.setattr(sp, "GithubIssueHandler", lambda *a, **k: object())

    # Patch subprocess.run to simulate failure
    monkeypatch.setattr(sp, "subprocess", SimpleNamespace(run=lambda *a, **k: DummyCompleted(returncode=1, stderr="fatal: could not push")))

    issue = SimpleNamespace(owner="someowner", repo="somerepo", head_branch="branch", number=1, thread_ids=None)

    with pytest.raises(RuntimeError):
        sp.update_existing_pull_request(
            issue=issue,
            token="token",
            username="user",
            platform=ProviderType.GITHUB,
            patch_dir="/tmp/patch",
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )


def test_update_azure_with_llm_and_replies_round_049(monkeypatch):
    """Test the AZURE_DEVOPS branch: successful push, LLM summarization, and replies.

    This test exercises:
    - platform AZURE_DEVOPS branch that splits owner into organization/project (lines ~509-516)
    - successful subprocess.run path
    - comment_message generation from additional_message JSON
    - LLM summarization path (lines ~568-583)
    - sending the final comment and replying to thread ids (lines ~590-601)
    """
    # Create a handler instance the test can inspect
    handler = DummyHandler()
    monkeypatch.setattr(sp, "ServiceContextIssue", lambda *_: handler)

    # Patch subprocess.run to simulate a successful git push
    monkeypatch.setattr(sp, "subprocess", SimpleNamespace(run=lambda *a, **k: DummyCompleted(returncode=0)))

    # Provide a non-None llm_config to trigger LLM summarization
    llm_config = SimpleNamespace()

    # Patch LLM to deterministic fake (already set in fixture) but ensure it's from module
    monkeypatch.setattr(sp, "LLM", DummyLLM)

    # Prepare an issue representing Azure DevOps with an owner containing org/project
    issue = SimpleNamespace(owner="organization/project", repo="repo", head_branch="the-branch", number=42, thread_ids=[101, 102])

    additional = json.dumps(["Fix A", "Fix B"])

    pr_url = sp.update_existing_pull_request(
        issue=issue,
        token="token",
        username=None,
        platform=ProviderType.AZURE_DEVOPS,
        patch_dir="/tmp/patch",
        llm_config=llm_config,
        comment_message=None,
        additional_message=additional,
        base_domain=None,
    )

    # The function should return the pull URL produced by the handler
    assert pr_url == handler.get_pull_url(42)

    # After summarization, send_comment_msg should have been called once with the LLM result
    assert len(handler.sent_comments) == 1
    sent_number, sent_msg = handler.sent_comments[0]
    assert sent_number == 42
    assert "LLM summarized output" in sent_msg

    # Replies: two explanations -> two replies recorded with matching thread ids and content
    assert len(handler.replies) == 2
    assert handler.replies[0][1] == 101
    assert handler.replies[1][1] == 102
    assert "Fix A" in handler.replies[0][2]
    assert "Fix B" in handler.replies[1][2]


def test_invalid_additional_message_triggers_fallback_and_reply_error_round_049(monkeypatch):
    """When additional_message is invalid JSON, ensure fallback messages are used and
    reply-loop exception path triggers sending an error message (lines ~584-585 and ~601-603).
    """
    handler = DummyHandler()
    monkeypatch.setattr(sp, "ServiceContextIssue", lambda *_: handler)

    # Successful push
    monkeypatch.setattr(sp, "subprocess", SimpleNamespace(run=lambda *a, **k: DummyCompleted(returncode=0)))

    issue = SimpleNamespace(owner="owner", repo="repo", head_branch="branch", number=7, thread_ids=[900])

    # invalid JSON for additional_message
    bad_additional = "not a json"

    pr_url = sp.update_existing_pull_request(
        issue=issue,
        token="token",
        username="user",
        platform=ProviderType.GITHUB,
        patch_dir="/tmp/patch",
        llm_config=None,
        comment_message=None,
        additional_message=bad_additional,
        base_domain=None,
    )

    # Function should still return the pull url
    assert pr_url == handler.get_pull_url(7)

    # Two messages should be sent: one fallback for the comment_message parse failure,
    # and one error message from the reply exception branch
    assert len(handler.sent_comments) == 2
    fallback_msg = handler.sent_comments[0][1]
    assert "failed to parse or summarize" in fallback_msg or "OpenHands update" in fallback_msg

    error_reply_msg = handler.sent_comments[1][1]
    assert "Error occurred when replying to threads; success explanations" in error_reply_msg
