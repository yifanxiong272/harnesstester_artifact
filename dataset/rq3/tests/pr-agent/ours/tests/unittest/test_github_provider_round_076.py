import types
import pytest

import pr_agent.git_providers.github_provider as gp


class DummyRepoObj:
    def __init__(self, default_branch):
        self.default_branch = default_branch


class DummyRepository:
    def __init__(self, default_branch):
        self.default_branch = default_branch


class DummyIssueMain:
    def __init__(self, html_url, repo_default_branch):
        self.html_url = html_url
        self.repository = DummyRepository(repo_default_branch)


class FakeLogger:
    def __init__(self):
        self.messages = []

    def error(self, msg):
        # record the message for assertion
        self.messages.append(msg)


def make_provider_instance():
    # Create instance without invoking __init__ to avoid external side effects
    prov = gp.GithubProvider.__new__(gp.GithubProvider)
    # Ensure attributes referenced by get_canonical_url_parts exist
    prov.issue_main = None
    prov.repo = None
    prov.base_url_html = None
    prov.repo_obj = None
    return prov


def test_get_canonical_with_repo_git_url_round_076(monkeypatch):
    """
    Case: repo_git_url provided and _get_owner_and_repo_path returns a valid 'owner/repo'.
    Expect: prefix constructed with provided desired_branch and suffix empty.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    prov = make_provider_instance()

    # Return a valid owner/repo path
    prov._get_owner_and_repo_path = lambda html_url: "alice/myrepo"

    repo_git_url = "https://git.example.com/alice/myrepo"
    desired_branch = "feature-branch"

    prefix, suffix = gp.GithubProvider.get_canonical_url_parts(prov, repo_git_url, desired_branch)

    assert prefix == "https://git.example.com/alice/myrepo/blob/feature-branch"
    assert suffix == ""
    # No error should have been logged
    assert fake_logger.messages == []


def test_get_canonical_with_issue_main_round_076(monkeypatch):
    """
    Case: no repo_git_url but issue_main present. desired_branch should come from issue_main.repository.default_branch
    and html_url from issue_main.html_url is parsed to derive scheme_and_netloc.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    prov = make_provider_instance()

    # Simulate issue_main with html_url
    prov.issue_main = DummyIssueMain("https://host.example.com/bob/theirrepo", "main-branch")
    # _get_owner_and_repo_path returns valid owner/repo
    prov._get_owner_and_repo_path = lambda html_url: "bob/theirrepo"

    # Call with repo_git_url None; desired_branch passed should be ignored and replaced by issue_main.repository.default_branch
    prefix, suffix = gp.GithubProvider.get_canonical_url_parts(prov, None, "ignored-branch")

    assert prefix == "https://host.example.com/bob/theirrepo/blob/main-branch"
    assert suffix == ""
    assert fake_logger.messages == []


def test_invalid_repo_path_logs_and_returns_empty_round_076(monkeypatch):
    """
    Case: repo_git_url provided but _get_owner_and_repo_path returns an invalid path (more than one '/').
    Expect: logs an error mentioning Invalid repo_path and returns ("", "").
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    prov = make_provider_instance()

    # Return an invalid repo path that does not have exactly one '/'
    prov._get_owner_and_repo_path = lambda html_url: "too/many/parts/extra"

    repo_git_url = "https://git.example.com/x/y/z"

    result = gp.GithubProvider.get_canonical_url_parts(prov, repo_git_url, "branch")

    assert result == ("", "")
    # Validate that an error was logged and mentions the invalid path
    assert any("Invalid repo_path" in m for m in fake_logger.messages)


def test_fallback_to_self_repo_and_missing_context_round_076(monkeypatch):
    """
    Case: no repo_git_url and no issue_main, but self.repo exists -> use self.repo and base_url_html and repo_obj.default_branch.
    Also test missing context entirely to hit the not all([...]) branch that logs an error and returns empty tuple.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: fake_logger)

    # First subcase: self.repo is used
    prov1 = make_provider_instance()
    prov1.repo = "charlie/repocharlie"
    prov1.base_url_html = "https://base.example.org"
    prov1.repo_obj = DummyRepoObj("repo-default")

    # _get_owner_and_repo_path should not be called in this subcase, but set something anyway
    prov1._get_owner_and_repo_path = lambda html_url: "unused/value"

    prefix1, suffix1 = gp.GithubProvider.get_canonical_url_parts(prov1, None, "ignored")

    assert prefix1 == "https://base.example.org/charlie/repocharlie/blob/repo-default"
    assert suffix1 == ""

    # Second subcase: completely missing context leads to error and empty return
    prov2 = make_provider_instance()
    # ensure no issue_main, no repo, no base url
    prov2.issue_main = None
    prov2.repo = None
    prov2.base_url_html = None
    prov2.repo_obj = None

    result2 = gp.GithubProvider.get_canonical_url_parts(prov2, None, "branch")
    assert result2 == ("", "")
    assert any("Unable to get canonical url parts" in m for m in fake_logger.messages)
