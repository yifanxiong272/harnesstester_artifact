# file: pr_agent/git_providers/github_provider.py:799-825
# asked: {"lines": [800, 802, 803, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 816, 817, 819, 820, 821, 822, 823, 825], "branches": [[802, 803], [802, 805], [806, 807], [806, 816], [807, 808], [807, 809], [816, 817], [816, 819]]}
# gained: {"lines": [800, 802, 803, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 816, 819, 820, 821, 822, 823, 825], "branches": [[802, 803], [802, 805], [806, 807], [806, 816], [807, 808], [807, 809], [816, 819]]}

import pytest
from pr_agent.git_providers.github_provider import GithubProvider


def _make_provider():
    # Instantiate without calling __init__ in case it requires arguments or side-effects.
    return object.__new__(GithubProvider)


def test_parse_standard_github_issue_url_valid():
    provider = _make_provider()
    repo, num = provider._parse_issue_url("https://github.com/owner/repo/issues/123")
    assert repo == "owner/repo"
    assert num == 123


def test_parse_standard_github_issue_url_non_int_raises():
    provider = _make_provider()
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url("https://github.com/owner/repo/issues/notanumber")
    assert "Unable to convert issue number to integer" in str(exc.value)


def test_parse_api_github_url_valid():
    provider = _make_provider()
    # api.github.com style path
    repo, num = provider._parse_issue_url("https://api.github.com/repos/owner/repo/issues/456")
    assert repo == "owner/repo"
    assert num == 456


def test_parse_api_github_url_invalid_structure_raises():
    provider = _make_provider()
    # Wrong structure: missing issue number (len < 5) should raise the ISSUE URL error
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url("https://api.github.com/repos/owner/repo/issues")
    assert "The provided URL does not appear to be a GitHub ISSUE URL" in str(exc.value)

    # Wrong structure: not 'issues' at expected position should also raise
    with pytest.raises(ValueError) as exc2:
        provider._parse_issue_url("https://api.github.com/repos/owner/repo/pulls/789")
    assert "The provided URL does not appear to be a GitHub ISSUE URL" in str(exc2.value)


def test_parse_api_v3_prefix_removal_and_valid():
    provider = _make_provider()
    # enterprise-style API prefix; code strips '/api/v3' then treats as API URL
    url = "https://github.example.com/api/v3/repos/owner/repo/issues/789"
    repo, num = provider._parse_issue_url(url)
    assert repo == "owner/repo"
    assert num == 789


def test_parse_api_v3_prefix_non_int_raises():
    provider = _make_provider()
    url = "https://github.example.com/api/v3/repos/owner/repo/issues/xyz"
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url(url)
    assert "Unable to convert issue number to integer" in str(exc.value)
