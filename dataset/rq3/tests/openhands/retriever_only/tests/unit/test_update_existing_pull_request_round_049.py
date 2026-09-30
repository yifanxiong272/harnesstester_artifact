import json
import types
import subprocess
import importlib
import pytest

# Load module under test
mod = importlib.import_module('openhands.resolver.send_pull_request')
update_existing_pull_request = mod.update_existing_pull_request
ProviderType = mod.ProviderType


class DummyHandler:
    """A minimal fake handler that records messages and provides expected APIs.

    The real handlers have many methods; update_existing_pull_request only
    needs get_authorize_url, get_pull_url, send_comment_msg and reply_to_comment.
    """

    def __init__(self, *args, **kwargs):
        self.sent_messages = []
        self.replies = []
        # store ctor args for debugging if needed
        self._ctor_args = (args, kwargs)

    def get_authorize_url(self):
        return 'https://example.com/'

    def get_pull_url(self, number):
        return f'http://pr/{number}'

    def send_comment_msg(self, number, message):
        # record (issue_number, message)
        self.sent_messages.append((number, message))

    def reply_to_comment(self, issue_number, comment_id, reply_comment):
        self.replies.append((issue_number, comment_id, reply_comment))


def _patch_handlers_and_service(monkeypatch, created_handlers=None):
    """Monkeypatch handler constructors and ServiceContextIssue in the module
    so the function uses DummyHandler instances and we can observe their calls.
    If created_handlers is provided, created handler instances are appended to it.
    """
    # All concrete handler constructors return a DummyHandler instance
    for name in (
        'GithubIssueHandler',
        'GitlabIssueHandler',
        'AzureDevOpsIssueHandler',
        'BitbucketIssueHandler',
        'BitbucketDCIssueHandler',
        'ForgejoIssueHandler',
    ):
        monkeypatch.setattr(mod, name, lambda *a, _name=name, **k: DummyHandler())

    def _service_context_issue(handler, llm_config):
        if created_handlers is not None:
            created_handlers.append(handler)
        return handler

    monkeypatch.setattr(mod, 'ServiceContextIssue', _service_context_issue)


def test_push_failure_round_049(monkeypatch):
    """If subprocess.run returns a non-zero exit code, update_existing_pull_request
    should log an error and raise a RuntimeError. This exercise covers the push
    failure branch (lines around 548-551).
    """
    _patch_handlers_and_service(monkeypatch)

    # Prepare a simple issue-like object with required attributes
    issue = types.SimpleNamespace(
        owner='owner',
        repo='repo',
        head_branch='feature-branch',
        number=1,
        thread_ids=[],
    )

    # Make subprocess.run simulate a failed push
    def _fake_run(*a, **k):
        return types.SimpleNamespace(returncode=2, stderr='simulated push error')

    monkeypatch.setattr(subprocess, 'run', _fake_run)

    with pytest.raises(RuntimeError) as exc:
        update_existing_pull_request(
            issue=issue,
            token='tok',
            username=None,
            platform=ProviderType.GITHUB,
            patch_dir='/tmp/patchdir',
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )

    assert 'Failed to push changes to the remote repository' in str(exc.value)


def test_azure_devops_json_parse_and_reply_error_round_049(monkeypatch):
    """Covers the Azure DevOps handler instantiation (owner split), the
    JSON parse failure paths for generating comment_message and for replying to
    threads (lines ~509-516, 584-585, 601-603). Ensures send_comment_msg is
    invoked with the fallback messages and that the function returns the
    handler's pull URL when push succeeds.
    """
    created = []
    _patch_handlers_and_service(monkeypatch, created_handlers=created)

    # Simulate successful git push
    def _fake_run_ok(*a, **k):
        return types.SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setattr(subprocess, 'run', _fake_run_ok)

    # Create an issue where owner contains 'organization/project' as required by AzureDevOps branch
    issue = types.SimpleNamespace(
        owner='org/project',
        repo='repo',
        head_branch='branch',
        number=42,
        thread_ids=[999],
    )

    # Provide an invalid JSON additional_message to trigger the JSONDecodeError paths
    bad_additional = 'not a json payload'

    pr_url = update_existing_pull_request(
        issue=issue,
        token='token',
        username=None,
        platform=ProviderType.AZURE_DEVOPS,
        patch_dir='/tmp/patchdir',
        llm_config=None,
        comment_message=None,
        additional_message=bad_additional,
        base_domain=None,
    )

    # The function should return the URL produced by DummyHandler.get_pull_url
    assert pr_url == 'http://pr/42'

    # We captured the handler instance created via ServiceContextIssue
    assert created, 'Expected a handler instance to be created and captured'
    handler = created[0]

    # Because additional_message failed to parse during comment generation, a fallback
    # message should have been sent once, and because replies failed to parse another
    # fallback message to threads should have been sent — resulting in at least two calls.
    assert len(handler.sent_messages) >= 2

    # Check that one of the sent messages includes the raw additional_message (fallback content)
    messages = [m for (_, m) in handler.sent_messages]
    assert any(bad_additional in m for m in messages)

    # The reply fallback message should mention 'Error occurred when replying to threads' or similar
    assert any('Error occurred when replying to threads' in m or 'failed to parse' in m for m in messages)
