# file: pr_agent/git_providers/bitbucket_server_provider.py:82-104
# asked: {"lines": [83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [85, 95], [89, 90], [89, 92], [95, 96], [95, 99], [97, 98], [97, 99], [99, 100], [99, 102]]}
# gained: {"lines": [83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [85, 95], [89, 90], [89, 92], [95, 96], [97, 98], [97, 99], [99, 100], [99, 102]]}

import pytest

from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider

class DummyBitbucketClient:
    def __init__(self, url="https://bb.example.com", default_branch=None, version="1.0"):
        self.url = url
        self._default_branch = default_branch
        self._version = version

    def get_default_branch(self, workspace, project):
        # mimic atlassian client method
        return self._default_branch if self._default_branch is not None else {}

    def get(self, path):
        # mimic the get used in __init__ to fetch version
        return {"version": self._version}

def make_provider_with_client(default_branch=None, url="https://bb.example.com"):
    client = DummyBitbucketClient(url=url, default_branch=default_branch)
    provider = BitbucketServerProvider(bitbucket_client=client)
    return provider

def test_get_canonical_url_parts_with_default_branch_displayId():
    provider = make_provider_with_client(default_branch={"displayId": "main"}, url="https://bb.example.com")
    # set workspace and repo slugs expected to be used when repo_git_url is None
    provider.workspace_slug = "WS"
    provider.repo_slug = "REPO"

    prefix, suffix = provider.get_canonical_url_parts(repo_git_url=None, desired_branch=None)

    assert prefix == "https://bb.example.com/projects/WS/repos/REPO/browse"
    assert suffix == "?at=refs%2Fheads%2Fmain"

def test_get_canonical_url_parts_with_default_branch_missing_displayId():
    provider = make_provider_with_client(default_branch={}, url="https://bb.example.com")
    provider.workspace_slug = "WS"
    provider.repo_slug = "REPO"

    prefix, suffix = provider.get_canonical_url_parts(repo_git_url=None, desired_branch=None)

    assert prefix == ""
    assert suffix == ""

def test_get_canonical_url_parts_with_repo_git_url_parsing():
    provider = make_provider_with_client(default_branch=None, url="https://bb.example.com")
    # don't set workspace/repo on provider so parsing from repo_git_url path is used
    repo_git_url = "https://bb.example.com/scm/WS/REPO.git"
    prefix, suffix = provider.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="dev")

    assert prefix == "https://bb.example.com/projects/WS/repos/REPO/browse"
    assert suffix == "?at=refs%2Fheads%2Fdev"

def test_get_canonical_url_parts_with_repo_git_url_bad_path():
    provider = make_provider_with_client(default_branch=None, url="https://bb.example.com")
    # a repo_path with more than one slash inside (after scm/) should not be accepted
    repo_git_url = "https://bb.example.com/scm/group/WS/REPO.git"
    prefix, suffix = provider.get_canonical_url_parts(repo_git_url=repo_git_url, desired_branch="dev")

    assert prefix == ""
    assert suffix == ""
