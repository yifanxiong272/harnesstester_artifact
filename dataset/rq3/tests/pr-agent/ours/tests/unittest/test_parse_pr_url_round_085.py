import pytest

from pr_agent.git_providers.github_provider import GithubProvider


def test_api_v3_url_success_round_085():
    url = "https://api.github.com/api/v3/repos/owner/repo/pulls/123"
    repo, number = GithubProvider._parse_pr_url(None, url)
    assert repo == "owner/repo"
    assert number == 123


def test_api_netloc_non_integer_pr_round_085():
    url = "https://api.github.com/repos/owner/repo/pulls/abc"
    with pytest.raises(ValueError) as exc:
        GithubProvider._parse_pr_url(None, url)
    assert str(exc.value) == "Unable to convert PR number to integer"


def test_api_netloc_wrong_segment_round_085():
    # valid api.github.com netloc but not a pulls path -> should raise
    url = "https://api.github.com/repos/owner/repo/issues/123"
    with pytest.raises(ValueError) as exc:
        GithubProvider._parse_pr_url(None, url)
    assert str(exc.value) == "The provided URL does not appear to be a GitHub PR URL"


def test_github_dotcom_pull_success_round_085():
    url = "https://github.com/owner/repo/pull/45"
    repo, number = GithubProvider._parse_pr_url(None, url)
    assert repo == "owner/repo"
    assert number == 45


def test_github_dotcom_insufficient_parts_round_085():
    # Missing the expected 'pull' and PR number segments
    url = "https://github.com/owner/repo"
    with pytest.raises(ValueError) as exc:
        GithubProvider._parse_pr_url(None, url)
    assert str(exc.value) == "The provided URL does not appear to be a GitHub PR URL"


def test_github_dotcom_non_integer_pr_round_085():
    url = "https://github.com/owner/repo/pull/notanumber"
    with pytest.raises(ValueError) as exc:
        GithubProvider._parse_pr_url(None, url)
    assert str(exc.value) == "Unable to convert PR number to integer"
