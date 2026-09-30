import pytest
from types import SimpleNamespace

from pr_agent.git_providers.github_provider import GithubProvider
from pr_agent.algo.utils import PRReviewHeader


def _make_provider_with_comments(comments):
    """Create a GithubProvider instance without running __init__ and attach a fake PR
    that yields the provided comments from get_issue_comments().
    """
    prov = object.__new__(GithubProvider)
    prov.pr = SimpleNamespace(get_issue_comments=lambda: list(comments))
    # ensure no pre-existing cached comments attribute
    if hasattr(prov, "comments"):
        delattr(prov, "comments")
    return prov


def test_raises_when_both_false_round_116():
    # If both full and incremental are False a ValueError must be raised
    prov = object.__new__(GithubProvider)
    # attach a minimal pr stub so attribute access inside the method won't fail
    prov.pr = SimpleNamespace(get_issue_comments=lambda: [])
    with pytest.raises(ValueError):
        prov.get_previous_review(full=False, incremental=False)


def test_returns_none_when_no_matching_prefix_round_116():
    # When comments exist but none start with the requested prefixes, None is returned
    comments = [SimpleNamespace(body="no-match-1"), SimpleNamespace(body="no-match-2")]
    prov = _make_provider_with_comments(comments)

    # Request only regular (full=True). No comment starts with the REGULAR prefix -> None
    result = prov.get_previous_review(full=True, incremental=False)
    assert result is None


def test_returns_most_recent_matching_comment_round_116():
    # Create comments where some start with REGULAR or INCREMENTAL prefixes
    comments = [
        SimpleNamespace(body="initial"),
        SimpleNamespace(body=PRReviewHeader.REGULAR.value + "-first"),
        SimpleNamespace(body=PRReviewHeader.INCREMENTAL.value + "-inc"),
        SimpleNamespace(body=PRReviewHeader.REGULAR.value + "-second"),
    ]

    # When both prefixes are requested, the function should return the most recent
    # comment (searches from the end). Here that's the REGULAR "-second" item.
    prov = _make_provider_with_comments(list(comments))
    res = prov.get_previous_review(full=True, incremental=True)
    assert res is not None
    assert res.body.startswith(PRReviewHeader.REGULAR.value)
    assert res.body.endswith("-second")

    # When only incremental=True, the most recent INCREMENTAL match should be returned
    prov2 = _make_provider_with_comments(list(comments))
    res2 = prov2.get_previous_review(full=False, incremental=True)
    assert res2 is not None
    assert res2.body.startswith(PRReviewHeader.INCREMENTAL.value)
    assert res2.body.endswith("-inc")
