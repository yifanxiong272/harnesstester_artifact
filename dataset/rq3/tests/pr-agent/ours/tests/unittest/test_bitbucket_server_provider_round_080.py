import pytest

import pr_agent.git_providers.bitbucket_server_provider as bbmod
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider


class LoggerMock:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # store the message for assertions
        self.errors.append(msg)


class DummyBitbucketClient:
    def __init__(self, default_branch_response=None):
        self._resp = default_branch_response or {}

    def get_default_branch(self, workspace_name, project_name):
        # mimic the real client method signature used by the function under test
        return self._resp


def make_provider_with_attrs(**attrs):
    # create instance without invoking __init__ to avoid side effects
    prov = object.__new__(BitbucketServerProvider)
    for k, v in attrs.items():
        setattr(prov, k, v)
    return prov


def test_get_canonical_url_parts_default_branch_round_080(monkeypatch):
    logger = LoggerMock()
    monkeypatch.setattr(bbmod, "get_logger", lambda: logger)

    bitbucket_client = DummyBitbucketClient(default_branch_response={"displayId": "main"})
    prov = make_provider_with_attrs(
        bitbucket_client=bitbucket_client,
        bitbucket_server_url="https://bb.example",
        workspace_slug="space",
        repo_slug="repo",
    )

    prefix, suffix = prov.get_canonical_url_parts(repo_git_url=None, desired_branch=None)

    assert prefix == "https://bb.example/projects/space/repos/repo/browse"
    assert suffix == "?at=refs%2Fheads%2Fmain"
    # no errors should have been logged
    assert logger.errors == []


def test_get_canonical_url_parts_default_branch_missing_round_080(monkeypatch):
    logger = LoggerMock()
    monkeypatch.setattr(bbmod, "get_logger", lambda: logger)

    # simulate missing displayId in response
    bitbucket_client = DummyBitbucketClient(default_branch_response={})
    prov = make_provider_with_attrs(
        bitbucket_client=bitbucket_client,
        bitbucket_server_url="https://bb.example",
        workspace_slug="workspaceX",
        repo_slug="projectY",
    )

    result = prov.get_canonical_url_parts(repo_git_url=None, desired_branch=None)

    # When default branch cannot be obtained, function returns empty tuple
    assert result == ("", "")
    # logger should have recorded an error mentioning the workspace and project
    assert len(logger.errors) == 1
    assert "workspace_name=workspaceX" in logger.errors[0]
    assert "project_name=projectY" in logger.errors[0]


def test_get_canonical_url_parts_from_git_url_valid_round_080(monkeypatch):
    logger = LoggerMock()
    monkeypatch.setattr(bbmod, "get_logger", lambda: logger)

    # No bitbucket_client needed for this branch
    prov = make_provider_with_attrs(
        bitbucket_client=None,
        bitbucket_server_url="https://bb.example",
        workspace_slug=None,
        repo_slug=None,
    )

    repo_git_url = "http://host/scm/space/myrepo.git"
    prefix, suffix = prov.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="feature-branch")

    assert prefix == "https://bb.example/projects/space/repos/myrepo/browse"
    assert suffix == "?at=refs%2Fheads%2Ffeature-branch"
    # ensure no error was logged for the happy path
    assert logger.errors == []


def test_get_canonical_url_parts_from_git_url_invalid_round_080(monkeypatch):
    logger = LoggerMock()
    monkeypatch.setattr(bbmod, "get_logger", lambda: logger)

    prov = make_provider_with_attrs(
        bitbucket_client=None,
        bitbucket_server_url="https://bb.example",
        workspace_slug=None,
        repo_slug=None,
    )

    # repo_path has too many parts -> should not set workspace/repo and return ("", "")
    repo_git_url = "http://host/scm/too/many/parts.git"
    result = prov.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="branch")

    assert result == ("", "")
    # error message should reference the git url
    assert any(repo_git_url in msg for msg in logger.errors)
