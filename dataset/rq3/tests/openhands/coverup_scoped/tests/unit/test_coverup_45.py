# file: openhands/resolver/interfaces/bitbucket.py:413-470
# asked: {"lines": [425, 426, 428, 429, 430, 432, 433, 435, 436, 437, 440, 441, 442, 443, 447, 448, 449, 450, 451, 452, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 468, 470], "branches": [[425, 426], [425, 428], [433, 435], [433, 470], [435, 436], [435, 440]]}
# gained: {"lines": [425, 426, 428, 429, 430, 432, 433, 435, 436, 437, 440, 441, 442, 443, 447, 448, 449, 450, 451, 452, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 468, 470], "branches": [[425, 426], [425, 428], [433, 435], [433, 470], [435, 436], [435, 440]]}

import pytest

from openhands.resolver.interfaces.bitbucket import BitbucketIssueHandler
from openhands.resolver.interfaces.issue import Issue


def test_get_converted_issues_raises_on_unspecified_issue_numbers():
    handler = BitbucketIssueHandler(owner="o", repo="r", token="t")
    with pytest.raises(ValueError) as exc:
        handler.get_converted_issues(None)
    assert "Unspecified issue numbers" in str(exc.value)


def test_get_converted_issues_filters_skips_and_converts(monkeypatch):
    handler = BitbucketIssueHandler(owner="owner", repo="repo", token="token")

    # Prepare issues to exercise branches:
    # 1: normal issue with content.raw and branch name
    issue1 = {
        "id": 1,
        "title": "Issue One",
        "content": {"raw": "Body One"},
        "source": {"branch": {"name": "branch-one"}},
    }
    # 2: has id but missing title -> should be skipped (warning branch)
    issue2 = {
        "id": 2,
        "title": None,
        "content": {"raw": "Body Two"},
        "source": {"branch": {"name": "branch-two"}},
    }
    # 3: PR-like with content=None -> body should become ''
    issue3 = {
        "id": 3,
        "title": "Issue Three",
        "content": None,
        "source": {},  # no branch name -> head_branch ''
    }
    # 4: has content dict but no raw -> body should default to ''
    issue4 = {
        "id": 4,
        "title": "Issue Four",
        "content": {},  # .get('raw','') will return ''
        "source": {"branch": {"name": "branch-four"}},
    }

    all_issues = [issue1, issue2, issue3, issue4]

    # Monkeypatch download_issues to return our prepared list
    monkeypatch.setattr(handler, "download_issues", lambda: all_issues)

    # Request conversion for all ids so filtering and skipping are exercised
    converted = handler.get_converted_issues(issue_numbers=[1, 2, 3, 4])

    # issue2 should be skipped because title is None, so expect 3 converted issues
    assert isinstance(converted, list)
    assert len(converted) == 3

    # Validate contents of converted issues by matching their numbers
    by_number = {iss.number: iss for iss in converted}

    # Issue 1 assertions
    iss1 = by_number[1]
    assert isinstance(iss1, Issue)
    assert iss1.number == 1
    assert iss1.title == "Issue One"
    assert iss1.body == "Body One"
    assert iss1.head_branch == "branch-one"
    # Lists should be present and empty as constructed in the handler
    assert iss1.closing_issues == []
    assert iss1.review_comments == []
    assert iss1.review_threads == []
    assert iss1.thread_ids == []
    assert iss1.thread_comments == []

    # Issue 3 assertions (content was None -> body '')
    iss3 = by_number[3]
    assert iss3.number == 3
    assert iss3.title == "Issue Three"
    assert iss3.body == ""  # content None should become empty string
    assert iss3.head_branch == ""  # no branch info provided

    # Issue 4 assertions (content dict without raw -> body defaults to '')
    iss4 = by_number[4]
    assert iss4.number == 4
    assert iss4.title == "Issue Four"
    assert iss4.body == ""
    assert iss4.head_branch == "branch-four"
