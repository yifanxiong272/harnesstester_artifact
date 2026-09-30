# file: pr_agent/git_providers/bitbucket_server_provider.py:82-104
# asked: {"lines": [83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [85, 95], [89, 90], [89, 92], [95, 96], [95, 99], [97, 98], [97, 99], [99, 100], [99, 102]]}
# gained: {"lines": [83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [85, 95], [89, 90], [89, 92], [95, 96], [97, 98], [97, 99], [99, 100], [99, 102]]}

import pytest
from types import SimpleNamespace

from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider

class DummyClient:
    def __init__(self, result):
        self.result = result
        self.called_with = None

    def get_default_branch(self, workspace, project):
        self.called_with = (workspace, project)
        return self.result

def make_provider(client=None, workspace_slug="WS", repo_slug="RP", server_url="http://bb"):
    # Instantiate without calling __init__
    prov = object.__new__(BitbucketServerProvider)
    prov.bitbucket_client = client
    prov.workspace_slug = workspace_slug
    prov.repo_slug = repo_slug
    prov.bitbucket_server_url = server_url
    return prov

def test_get_canonical_url_parts_uses_default_branch_when_present():
    client = DummyClient({"displayId": "main"})
    prov = make_provider(client=client, workspace_slug="myws", repo_slug="myrepo", server_url="https://example.com")
    prefix, suffix = prov.get_canonical_url_parts(repo_git_url=None, desired_branch=None)
    assert client.called_with == ("myws", "myrepo")
    assert prefix == "https://example.com/projects/myws/repos/myrepo/browse"
    assert suffix == "?at=refs%2Fheads%2Fmain"

def test_get_canonical_url_parts_returns_empty_when_default_branch_missing():
    client = DummyClient({"nope": "value"})
    prov = make_provider(client=client, workspace_slug="abc", repo_slug="def", server_url="https://bb")
    res = prov.get_canonical_url_parts(repo_git_url=None, desired_branch=None)
    assert client.called_with == ("abc", "def")
    assert res == ("", "")

def test_get_canonical_url_parts_parses_repo_git_url_successfully():
    # client should not be called in this branch
    client = DummyClient({"displayId": "should_not_be_used"})
    prov = make_provider(client=client, server_url="http://bbserver")
    repo_git_url = "http://host/scm/WSNAME/REPO123.git"
    prefix, suffix = prov.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="feature-branch")
    assert client.called_with is None
    assert prefix == "http://bbserver/projects/WSNAME/repos/REPO123/browse"
    assert suffix == "?at=refs%2Fheads%2Ffeature-branch"

def test_get_canonical_url_parts_returns_empty_for_malformed_repo_path():
    # repo path has more than one slash so parsing should fail and return empty
    client = DummyClient({"displayId": "unused"})
    prov = make_provider(client=client, server_url="http://bb")
    repo_git_url = "http://host/scm/WS/REPO/extra.git"
    res = prov.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="dev")
    # client should not be called because repo_git_url was provided
    assert client.called_with is None
    assert res == ("", "")
