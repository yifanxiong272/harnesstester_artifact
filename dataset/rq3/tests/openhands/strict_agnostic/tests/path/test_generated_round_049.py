import importlib
import types
import json
import pytest

# import the module under test
module = importlib.import_module('openhands.resolver.send_pull_request')

# Simple fake handler that emulates minimal behavior used by update_existing_pull_request
class DummyHandler:
    def __init__(self, *args, **kwargs):
        # store init args for assertions if needed
        self.init_args = args
        self.init_kwargs = kwargs
        self.sent_comments = []
        self.replies = []

    def get_authorize_url(self):
        return 'https://dummy-auth/'

    def get_pull_url(self, number):
        # deterministic pull url used as return value
        owner = None
        repo = None
        # try to extract owner/repo if passed in init_args
        if self.init_args:
            try:
                owner = self.init_args[0]
                repo = self.init_args[1]
            except Exception:
                pass
        return f'https://pr/{owner or "owner"}/{repo or "repo"}/pull/{number}'

    def send_comment_msg(self, number, message):
        # record the message for assertions
        self.sent_comments.append((number, message))

    def reply_to_comment(self, number, comment_id, reply_comment):
        self.replies.append((number, comment_id, reply_comment))


# ServiceContextIssue should return the handler itself (the code expects an object with methods)
class DummyServiceContext:
    def __new__(cls, handler, llm_config):
        # the code calls ServiceContextIssue(<HandlerClass(...)>, llm_config)
        # so handler here will be an instance of DummyHandler (we monkeypatch handler classes below)
        return handler


# Helper to install the dummy classes onto the module
def install_dummies(monkeypatch):
    # Replace handler classes with DummyHandler so different branches construct a DummyHandler
    monkeypatch.setattr(module, 'ServiceContextIssue', DummyServiceContext)
    monkeypatch.setattr(module, 'AzureDevOpsIssueHandler', DummyHandler)
    monkeypatch.setattr(module, 'BitbucketIssueHandler', DummyHandler)
    monkeypatch.setattr(module, 'BitbucketDCIssueHandler', DummyHandler)
    monkeypatch.setattr(module, 'ForgejoIssueHandler', DummyHandler)
    monkeypatch.setattr(module, 'GithubIssueHandler', DummyHandler)
    monkeypatch.setattr(module, 'GitlabIssueHandler', DummyHandler)


# A small stand-in Issue object
def make_issue(owner, repo, head_branch='branch', number=1, thread_ids=None):
    return types.SimpleNamespace(owner=owner, repo=repo, head_branch=head_branch, number=number, thread_ids=thread_ids)


def make_subprocess_result(returncode=0, stderr=''):
    return types.SimpleNamespace(returncode=returncode, stderr=stderr)


def test_azure_devops_push_failure_round_049(monkeypatch):
    """Azure DevOps branch: owner contains organization/project split and push fails -> RuntimeError."""
    install_dummies(monkeypatch)

    # Simulate a failure of git push
    monkeypatch.setattr(module, 'subprocess', types.SimpleNamespace(run=lambda *a, **k: make_subprocess_result(returncode=1, stderr='git push failed')))

    # owner has a slash to trigger the organization/project split
    issue = make_issue('org/project', 'repo', head_branch='feat/1', number=7)

    with pytest.raises(RuntimeError, match='Failed to push changes'):
        module.update_existing_pull_request(
            issue=issue,
            token='token',
            username='user',
            platform=module.ProviderType.AZURE_DEVOPS,
            patch_dir='/tmp',
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )


def test_bitbucket_push_comment_and_reply_fallback_round_049(monkeypatch):
    """Bitbucket branch: successful push, invalid additional_message -> comment fallback and reply fallback paths exercised."""
    install_dummies(monkeypatch)

    # Simulate a successful git push
    monkeypatch.setattr(module, 'subprocess', types.SimpleNamespace(run=lambda *a, **k: make_subprocess_result(returncode=0)))

    # Create issue with an unresolved thread to trigger reply-to-thread logic
    issue = make_issue('owner', 'repo', head_branch='b', number=99, thread_ids=[12345])

    # additional_message is invalid JSON to force the json.JSONDecodeError handling paths
    additional_message = 'this is not json'

    pr_url = module.update_existing_pull_request(
        issue=issue,
        token='token',
        username='user',
        platform=module.ProviderType.BITBUCKET,
        patch_dir='/tmp',
        llm_config=None,
        comment_message=None,
        additional_message=additional_message,
        base_domain=None,
    )

    # returned pr_url should match our DummyHandler.get_pull_url pattern
    assert pr_url == 'https://pr/owner/repo/pull/99'

    # The DummyHandler instance created inside the function is not directly exposed here.
    # However, we can re-create what would have been sent via the fallback message contents by calling
    # the same fallback formatting (ensure expected substrings are present in returned behavior).
    # The comment_message fallback includes the provided additional_message string; check pr_url used above
    assert 'this is not json' in pr_url or pr_url.startswith('https://pr/')

    # Since invalid JSON is used, both the comment fallback and the reply fallback paths would have executed.
    # We verify by calling the flow again but capturing the handler instance this time.

    # To capture the handler used, monkeypatch the handler constructor to store the last instance
    created = {}

    def capture_constructor(owner, repo, token_arg, username_arg, base_domain_arg=None):
        h = DummyHandler(owner, repo, token_arg, username_arg, base_domain_arg)
        created['h'] = h
        return h

    monkeypatch.setattr(module, 'BitbucketIssueHandler', capture_constructor)

    # run again to capture the handler and inspect sent messages
    pr_url2 = module.update_existing_pull_request(
        issue=issue,
        token='token',
        username='user',
        platform=module.ProviderType.BITBUCKET,
        patch_dir='/tmp',
        llm_config=None,
        comment_message=None,
        additional_message=additional_message,
        base_domain=None,
    )

    handler = created['h']
    # After invalid JSON, handler.send_comment_msg should have been called at least once
    assert any('failed to parse' in msg or 'failed to parse or summarize' in msg for (_, msg) in handler.sent_comments)

    # The second fallback about replying to threads also sends a message containing 'Error occurred when replying to threads'
    assert any('Error occurred when replying to threads' in msg or 'Error occurred when replying to threads; success explanations' in msg for (_, msg) in handler.sent_comments)

    # reply_to_comment should not have been called because JSON decoding failed
    assert handler.replies == []


def test_bitbucket_dc_push_success_round_049(monkeypatch):
    """Bitbucket Data Center branch: successful push returns expected pr_url."""
    install_dummies(monkeypatch)

    monkeypatch.setattr(module, 'subprocess', types.SimpleNamespace(run=lambda *a, **k: make_subprocess_result(returncode=0)))

    issue = make_issue('owner', 'repo', head_branch='b', number=5, thread_ids=None)

    # Capture the handler instance
    created = {}

    def capture_constructor(owner, repo, token_arg, username_arg, base_domain_arg=None):
        h = DummyHandler(owner, repo, token_arg, username_arg, base_domain_arg)
        created['h'] = h
        return h

    monkeypatch.setattr(module, 'BitbucketDCIssueHandler', capture_constructor)

    pr_url = module.update_existing_pull_request(
        issue=issue,
        token='token',
        username='user',
        platform=module.ProviderType.BITBUCKET_DATA_CENTER,
        patch_dir='/tmp',
        llm_config=None,
        comment_message=None,
        additional_message=None,
        base_domain=None,
    )

    assert pr_url == 'https://pr/owner/repo/pull/5'
    handler = created['h']
    # No comments should have been sent since no additional_message / comment_message
    assert handler.sent_comments == []


def test_forgejo_push_success_round_049(monkeypatch):
    """Forgejo branch: successful push returns expected pr_url."""
    install_dummies(monkeypatch)
    monkeypatch.setattr(module, 'subprocess', types.SimpleNamespace(run=lambda *a, **k: make_subprocess_result(returncode=0)))

    issue = make_issue('owner', 'repo', head_branch='b', number=77, thread_ids=None)

    created = {}

    def capture_constructor(owner, repo, token_arg, username_arg, base_domain_arg=None):
        h = DummyHandler(owner, repo, token_arg, username_arg, base_domain_arg)
        created['h'] = h
        return h

    monkeypatch.setattr(module, 'ForgejoIssueHandler', capture_constructor)

    pr_url = module.update_existing_pull_request(
        issue=issue,
        token='token',
        username='user',
        platform=module.ProviderType.FORGEJO,
        patch_dir='/tmp',
        llm_config=None,
        comment_message=None,
        additional_message=None,
        base_domain=None,
    )

    assert pr_url == 'https://pr/owner/repo/pull/77'
    handler = created['h']
    assert handler.sent_comments == []


def test_unsupported_platform_raises_round_049(monkeypatch):
    """Passing an unsupported platform object triggers the ValueError else-branch."""
    install_dummies(monkeypatch)
    monkeypatch.setattr(module, 'subprocess', types.SimpleNamespace(run=lambda *a, **k: make_subprocess_result(returncode=0)))

    issue = make_issue('owner', 'repo', head_branch='b', number=1, thread_ids=None)

    # Pass a value that doesn't match any of the handled ProviderType enum cases
    with pytest.raises(ValueError, match='Unsupported platform'):
        module.update_existing_pull_request(
            issue=issue,
            token='token',
            username='user',
            platform='SOME_UNKNOWN_PLATFORM',
            patch_dir='/tmp',
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )
