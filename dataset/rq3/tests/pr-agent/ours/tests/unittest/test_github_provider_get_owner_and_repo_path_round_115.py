import types
import pr_agent.git_providers.github_provider as gp


class FakeLogger:
    def __init__(self):
        self.errors = []
        self.exceptions = []

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


class DummySelf:
    """A minimal object that can be used as `self` when calling the
    unbound GithubProvider._get_owner_and_repo_path function. Tests will
    attach the necessary parsing methods to instances of this class.
    """
    pass


def test_issues_url_round_115():
    fake_logger = FakeLogger()
    # patch module-level get_logger used by the function
    gp.get_logger = lambda: fake_logger

    inst = DummySelf()

    # attach a _parse_issue_url that returns a repo path and some extra val
    def parse_issue(url):
        return ("owner/issues-repo", "42")

    inst._parse_issue_url = parse_issue

    # Call the unbound function with our dummy instance
    result = gp.GithubProvider._get_owner_and_repo_path(inst, "https://api.github.com/repos/owner/issues/1")

    assert result == "owner/issues-repo"
    # no error/exception should have been logged
    assert fake_logger.errors == []
    assert fake_logger.exceptions == []


def test_pull_url_round_115():
    fake_logger = FakeLogger()
    gp.get_logger = lambda: fake_logger

    inst = DummySelf()

    def parse_pr(url):
        return ("owner/pr-repo", "17")

    inst._parse_pr_url = parse_pr

    result = gp.GithubProvider._get_owner_and_repo_path(inst, "https://github.com/owner/pr/123/pull")

    assert result == "owner/pr-repo"
    assert fake_logger.errors == []
    assert fake_logger.exceptions == []


def test_git_url_round_115():
    fake_logger = FakeLogger()
    gp.get_logger = lambda: fake_logger

    inst = DummySelf()

    # No parse_issue/_parse_pr present/required for this path; ensure .git branch is used
    git_url = "https://github.com/someowner/somerepo.git"
    result = gp.GithubProvider._get_owner_and_repo_path(inst, git_url)

    assert result == "someowner/somerepo"
    assert fake_logger.errors == []
    assert fake_logger.exceptions == []


def test_unrecognized_url_round_115():
    fake_logger = FakeLogger()
    gp.get_logger = lambda: fake_logger

    inst = DummySelf()

    # URL that does not contain 'issues', 'pull' and does not end with .git
    bad_url = "https://example.com/random/path"
    result = gp.GithubProvider._get_owner_and_repo_path(inst, bad_url)

    assert result == ""  # should return empty string on unrecognized url
    # the error message should include the original url
    assert any(bad_url in msg for msg in fake_logger.errors)
    assert fake_logger.exceptions == []


def test_parse_exception_round_115():
    fake_logger = FakeLogger()
    gp.get_logger = lambda: fake_logger

    inst = DummySelf()

    # Make _parse_issue_url raise to trigger the except: branch
    def parse_issue_raises(url):
        raise RuntimeError("boom")

    inst._parse_issue_url = parse_issue_raises

    bad_issues_url = "https://github.com/owner/issues/999"
    result = gp.GithubProvider._get_owner_and_repo_path(inst, bad_issues_url)

    assert result == ""  # exception path returns empty string
    # exception logger should have been called and include the url
    assert any(bad_issues_url in msg for msg in fake_logger.exceptions)
