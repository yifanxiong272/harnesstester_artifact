# file: pr_agent/git_providers/github_provider.py:799-825
# asked: {"lines": [800, 802, 803, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 816, 817, 819, 820, 821, 822, 823, 825], "branches": [[802, 803], [802, 805], [806, 807], [806, 816], [807, 808], [807, 809], [816, 817], [816, 819]]}
# gained: {"lines": [800, 802, 803, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 816, 817, 819, 820, 821, 822, 823, 825], "branches": [[802, 803], [802, 805], [806, 807], [806, 816], [807, 808], [807, 809], [816, 817], [816, 819]]}

import pytest
from pr_agent.git_providers.github_provider import GithubProvider

def make_provider():
    # Create instance without running __init__ to avoid external side effects.
    return GithubProvider.__new__(GithubProvider)

def test_parse_issue_url_api_v3_success():
    provider = make_provider()
    url = "https://api.github.com/api/v3/repos/owner/repo/issues/123"
    repo, num = provider._parse_issue_url(url)
    assert repo == "owner/repo"
    assert num == 123

def test_parse_issue_url_api_v3_bad_path_raises():
    provider = make_provider()
    url = "https://api.github.com/api/v3/repos/owner/repo/pulls/123"
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url(url)
    assert "The provided URL does not appear to be a GitHub ISSUE URL" in str(exc.value)

def test_parse_issue_url_api_v3_invalid_issue_number():
    provider = make_provider()
    url = "https://api.github.com/api/v3/repos/owner/repo/issues/abc"
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url(url)
    assert str(exc.value) == "Unable to convert issue number to integer"

def test_parse_issue_url_normal_success():
    provider = make_provider()
    url = "https://github.com/owner/repo/issues/456"
    repo, num = provider._parse_issue_url(url)
    assert repo == "owner/repo"
    assert num == 456

def test_parse_issue_url_normal_bad_path_raises():
    provider = make_provider()
    url = "https://github.com/owner/repo/pull/456"
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url(url)
    assert "The provided URL does not appear to be a GitHub PR issue" in str(exc.value)

def test_parse_issue_url_normal_invalid_issue_number():
    provider = make_provider()
    url = "https://github.com/owner/repo/issues/xyz"
    with pytest.raises(ValueError) as exc:
        provider._parse_issue_url(url)
    assert str(exc.value) == "Unable to convert issue number to integer"
