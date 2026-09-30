# file: pr_agent/git_providers/github_provider.py:771-797
# asked: {"lines": [772, 774, 775, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 788, 789, 791, 792, 793, 794, 795, 797], "branches": [[774, 775], [774, 777], [778, 779], [778, 788], [779, 780], [779, 781], [788, 789], [788, 791]]}
# gained: {"lines": [772, 774, 775, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 788, 789, 791, 792, 793, 794, 795, 797], "branches": [[774, 775], [774, 777], [778, 779], [778, 788], [779, 780], [779, 781], [788, 789], [788, 791]]}

import pytest
from pr_agent.git_providers import github_provider


def _make_provider():
    # Create instance without calling __init__ to avoid side effects
    return object.__new__(github_provider.GithubProvider)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://api.github.com/api/v3/repos/owner/repo/pulls/123", ("owner/repo", 123)),
        ("https://github.com/owner/repo/pull/456", ("owner/repo", 456)),
    ],
)
def test_parse_pr_url_success(url, expected):
    gp = _make_provider()
    result = github_provider.GithubProvider._parse_pr_url(gp, url)
    assert result == expected


def test_parse_pr_url_api_non_integer_pr():
    gp = _make_provider()
    url = "https://api.github.com/api/v3/repos/owner/repo/pulls/notanint"
    with pytest.raises(ValueError) as excinfo:
        github_provider.GithubProvider._parse_pr_url(gp, url)
    assert "Unable to convert PR number to integer" in str(excinfo.value)


def test_parse_pr_url_api_invalid_path():
    gp = _make_provider()
    url = "https://api.github.com/api/v3/repos/owner/repo/issues/123"
    with pytest.raises(ValueError) as excinfo:
        github_provider.GithubProvider._parse_pr_url(gp, url)
    assert "The provided URL does not appear to be a GitHub PR URL" in str(excinfo.value)


def test_parse_pr_url_web_non_integer_pr():
    gp = _make_provider()
    url = "https://github.com/owner/repo/pull/notint"
    with pytest.raises(ValueError) as excinfo:
        github_provider.GithubProvider._parse_pr_url(gp, url)
    assert "Unable to convert PR number to integer" in str(excinfo.value)


def test_parse_pr_url_web_insufficient_parts():
    gp = _make_provider()
    url = "https://github.com/owner/repo"
    with pytest.raises(ValueError) as excinfo:
        github_provider.GithubProvider._parse_pr_url(gp, url)
    assert "The provided URL does not appear to be a GitHub PR URL" in str(excinfo.value)
