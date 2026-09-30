# file: pr_agent/git_providers/github_provider.py:771-797
# asked: {"lines": [772, 774, 775, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 788, 789, 791, 792, 793, 794, 795, 797], "branches": [[774, 775], [774, 777], [778, 779], [778, 788], [779, 780], [779, 781], [788, 789], [788, 791]]}
# gained: {"lines": [772, 774, 775, 777, 778, 779, 780, 781, 782, 783, 786, 788, 789, 791, 792, 793, 794, 795, 797], "branches": [[774, 775], [774, 777], [778, 779], [778, 788], [779, 780], [779, 781], [788, 789], [788, 791]]}

import pytest
from urllib.parse import urlparse

from pr_agent.git_providers.github_provider import GithubProvider


def _call_parse(pr_url: str):
    # create an instance without running __init__ to avoid side effects
    gp = object.__new__(GithubProvider)
    return GithubProvider._parse_pr_url(gp, pr_url)


def test_parse_api_github_url_valid():
    url = "https://api.github.com/repos/owner/repo/pulls/123"
    repo, num = _call_parse(url)
    assert repo == "owner/repo"
    assert num == 123


def test_parse_api_v3_prefix_url_valid():
    url = "https://github.example.com/api/v3/repos/owner/repo/pulls/456"
    repo, num = _call_parse(url)
    assert repo == "owner/repo"
    assert num == 456


def test_parse_api_github_url_invalid_path_raises():
    # Less than 5 path parts for API style should raise
    url = "https://api.github.com/owner/repo/notpulls/123"
    with pytest.raises(ValueError) as exc:
        _call_parse(url)
    assert "The provided URL does not appear to be a GitHub PR URL" in str(exc.value)


def test_parse_normal_url_valid():
    url = "https://github.com/owner/repo/pull/789"
    repo, num = _call_parse(url)
    assert repo == "owner/repo"
    assert num == 789


def test_parse_normal_url_bad_pr_number_raises():
    url = "https://github.com/owner/repo/pull/notanumber"
    with pytest.raises(ValueError) as exc:
        _call_parse(url)
    assert "Unable to convert PR number to integer" in str(exc.value)


def test_parse_normal_url_invalid_path_raises():
    url = "https://github.com/owner/repo/notpull/123"
    with pytest.raises(ValueError) as exc:
        _call_parse(url)
    assert "The provided URL does not appear to be a GitHub PR URL" in str(exc.value)
