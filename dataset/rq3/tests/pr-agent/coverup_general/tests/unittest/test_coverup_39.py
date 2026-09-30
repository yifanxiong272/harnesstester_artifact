# file: pr_agent/git_providers/github_provider.py:116-143
# asked: {"lines": [117, 118, 119, 121, 122, 123, 124, 125, 126, 127, 128, 130, 131, 133, 134, 135, 136, 137, 138, 139, 141, 142, 143], "branches": [[121, 122], [121, 133], [127, 128], [127, 130], [133, 134], [133, 137], [137, 138], [137, 141]]}
# gained: {"lines": [117, 118, 119, 121, 122, 123, 124, 125, 126, 127, 128, 130, 131, 133, 134, 135, 136, 137, 138, 139, 141, 142, 143], "branches": [[121, 122], [121, 133], [127, 128], [127, 130], [133, 134], [133, 137], [137, 138], [137, 141]]}

import pytest
from types import SimpleNamespace
from urllib.parse import urlparse

import pr_agent.git_providers.github_provider as gpmod
from pr_agent.git_providers.github_provider import GithubProvider


@pytest.fixture(autouse=True)
def no_network_github_client(monkeypatch):
    # Prevent GithubProvider from trying to create a real github client during init
    monkeypatch.setattr(gpmod.GithubProvider, "_get_github_client", lambda self: None)
    yield


def test_get_canonical_url_parts_with_repo_git_url_valid(monkeypatch):
    provider = GithubProvider()

    # Simulate _get_owner_and_repo_path returning a valid "<owner>/<repo>"
    monkeypatch.setattr(provider, "_get_owner_and_repo_path", lambda url: "owner/repo")

    repo_git_url = "https://github.com/owner/repo"
    desired_branch = "main"

    prefix, suffix = provider.get_canonical_url_parts(repo_git_url, desired_branch)

    parsed = urlparse(repo_git_url)
    expected_scheme_netloc = f"{parsed.scheme}://{parsed.netloc}"
    expected_prefix = f"{expected_scheme_netloc}/owner/repo/blob/{desired_branch}"
    assert prefix == expected_prefix
    assert suffix == ""


def test_get_canonical_url_parts_with_repo_git_url_invalid_repo_path(monkeypatch):
    provider = GithubProvider()

    # Simulate _get_owner_and_repo_path returning an invalid path (more than one slash)
    monkeypatch.setattr(provider, "_get_owner_and_repo_path", lambda url: "a/b/c")

    repo_git_url = "https://github.com/a/b/c"
    desired_branch = "main"

    prefix, suffix = provider.get_canonical_url_parts(repo_git_url, desired_branch)

    # Should return empty tuple when repo_path invalid
    assert prefix == ""
    assert suffix == ""


def test_get_canonical_url_parts_falls_back_to_self_repo(monkeypatch):
    provider = GithubProvider()

    # No external url and no issue_main, but provider.repo is set
    provider.repo = "foo/bar"
    provider.base_url_html = "https://github.com"
    provider.repo_obj = SimpleNamespace(default_branch="develop")

    prefix, suffix = provider.get_canonical_url_parts(None, "ignored-branch")

    expected_prefix = "https://github.com/foo/bar/blob/develop"
    assert prefix == expected_prefix
    assert suffix == ""


def test_get_canonical_url_parts_missing_context_returns_empty(monkeypatch):
    provider = GithubProvider()

    # Ensure no repo_git_url, no issue_main, and no repo set -> should return ("", "")
    provider.repo = None
    provider.issue_main = None

    prefix, suffix = provider.get_canonical_url_parts(None, "main")

    assert prefix == ""
    assert suffix == ""
