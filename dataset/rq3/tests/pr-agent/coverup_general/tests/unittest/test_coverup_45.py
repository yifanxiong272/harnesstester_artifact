# file: pr_agent/git_providers/github_provider.py:33-59
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59], "branches": [[51, 52], [51, 56], [56, 57], [56, 59]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59], "branches": [[51, 52], [51, 56], [56, 57], [56, 59]]}

import pytest

from types import SimpleNamespace


def make_dummy_settings(base_url: str):
    class DummySettings:
        def get(self, key, default=None):
            return base_url
    return DummySettings()


def test_init_no_pr_sets_pr_commits_none_and_base_urls(monkeypatch):
    import pr_agent.git_providers.github_provider as gp

    # context.get returns an installation id
    monkeypatch.setattr(gp.context, "get", lambda key, default=None: "inst-123")

    # make get_settings return a base_url containing 'api/' (with trailing slash) to exercise behavior
    monkeypatch.setattr(gp, "get_settings", lambda: make_dummy_settings("https://example.com/api/"))

    # avoid real GitHub client creation
    monkeypatch.setattr(gp.GithubProvider, "_get_github_client", lambda self: "fake-client")

    # Instantiate without pr_url to hit the else branch that sets pr_commits = None
    provider = gp.GithubProvider(pr_url=None)

    # Assertions for attributes set in __init__
    assert provider.repo_obj is None
    assert provider.installation_id == "inst-123"
    assert provider.max_comment_chars == 65000
    # base_url should have trailing slash stripped
    assert provider.base_url == "https://example.com/api"
    # Because the implementation checks for the substring 'api/' in base_url (after rstrip),
    # and rstrip removed the trailing slash, base_url_html will fall back to 'https://github.com'
    assert provider.base_url_html == "https://github.com"
    assert provider.github_client == "fake-client"
    # pr_commits is explicitly set to None in the else branch
    assert hasattr(provider, "pr_commits")
    assert provider.pr_commits is None


def test_init_with_pull_url_handles_set_pr_and_commits(monkeypatch):
    import pr_agent.git_providers.github_provider as gp

    # Make context.get raise an exception to exercise the try/except (installation_id -> None)
    def raise_exc(key, default=None):
        raise Exception("context error")

    monkeypatch.setattr(gp.context, "get", raise_exc)

    # settings
    monkeypatch.setattr(gp, "get_settings", lambda: make_dummy_settings("https://example.com/api/"))

    # avoid creating a real github client
    monkeypatch.setattr(gp.GithubProvider, "_get_github_client", lambda self: "fake-client")

    # Patch set_pr to set a fake pr object with get_commits returning an iterable
    def fake_set_pr(self, pr_url):
        class FakePR:
            def get_commits(self_inner):
                # return an iterable of commits (could be strings/ids)
                return ["commit1", "commit2", "commit3"]
        self.pr = FakePR()

    monkeypatch.setattr(gp.GithubProvider, "set_pr", fake_set_pr)

    # Patch get_pr_url to return a canonical html URL for the PR
    monkeypatch.setattr(gp.GithubProvider, "get_pr_url", lambda self: "https://example.com/org/repo/pull/5")

    # Instantiate with a PR URL (contains 'pull') to exercise that branch
    provider = gp.GithubProvider(pr_url="https://api.example.com/repos/org/repo/pull/5")

    # installation_id should be None due to raised exception
    assert provider.installation_id is None

    # set_pr should have been called and pr_commits populated
    assert isinstance(provider.pr_commits, list)
    assert provider.pr_commits == ["commit1", "commit2", "commit3"]

    # last_commit_id should be the last element of pr_commits
    assert provider.last_commit_id == "commit3"

    # pr_url should have been replaced by get_pr_url result
    assert provider.pr_url == "https://example.com/org/repo/pull/5"


def test_init_with_issue_url_sets_issue_main_and_leaves_pr_commits_unset(monkeypatch):
    import pr_agent.git_providers.github_provider as gp

    # context.get returns installation id
    monkeypatch.setattr(gp.context, "get", lambda key, default=None: "inst-xyz")

    # settings
    monkeypatch.setattr(gp, "get_settings", lambda: make_dummy_settings("https://api.github.com"))

    # avoid creating a real github client
    monkeypatch.setattr(gp.GithubProvider, "_get_github_client", lambda self: "fake-client")

    # Patch _get_issue_handle to return a sentinel issue object
    monkeypatch.setattr(gp.GithubProvider, "_get_issue_handle", lambda self, url: SimpleNamespace(id=42, url=url))

    # Instantiate with an issue URL to exercise the 'issue' branch
    issue_url = "https://api.example.com/repos/org/repo/issues/7"
    provider = gp.GithubProvider(pr_url=issue_url)

    # issue_main should be set to the sentinel object
    assert hasattr(provider, "issue_main")
    assert getattr(provider.issue_main, "id") == 42
    assert getattr(provider.issue_main, "url") == issue_url

    # In the 'issue' branch pr_commits should not be created by __init__
    assert not hasattr(provider, "pr_commits")
