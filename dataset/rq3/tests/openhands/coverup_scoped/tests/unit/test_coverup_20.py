# file: openhands/resolver/interfaces/forgejo.py:427-487
# asked: {"lines": [430, 431, 433, 434, 435, 437, 438, 439, 440, 441, 444, 445, 446, 447, 448, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 462, 463, 464, 465, 466, 467, 468, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 485, 487], "branches": [[430, 431], [430, 433], [445, 446], [445, 487], [446, 447], [446, 450]]}
# gained: {"lines": [430, 431, 433, 434, 435, 437, 438, 439, 440, 441, 444, 445, 446, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 462, 463, 464, 465, 466, 467, 468, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 485, 487], "branches": [[430, 431], [430, 433], [445, 446], [445, 487], [446, 450]]}

import types
import httpx
import pytest

from openhands.resolver.interfaces.forgejo import ForgejoPRHandler
from openhands.resolver.interfaces.issue import Issue


def make_fake_response(all_prs):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return all_prs

    return FakeResponse()


def make_fake_self():
    fake = types.SimpleNamespace()
    # attributes used by the method
    fake.download_url = "https://fake.example/prs"
    fake.headers = {"Authorization": "token"}
    fake.owner = "octo"
    fake.repo = "repo"

    # helper methods expected by get_converted_issues
    fake._to_int = lambda v: int(v) if v is not None else 0

    def download_pr_metadata(pr_number, comment_id):
        # return distinct values per PR number to assert mapping
        return (
            [f"closing-{pr_number}"],  # closing_issues
            [pr_number + 100],         # closing_issue_numbers
            [f"review_comment-{pr_number}"],  # review_comments
            [{"comment": f"rt-{pr_number}", "files": [f"file-{pr_number}"]}],   # review_threads as dicts
            [str(pr_number + 1000)],    # thread_ids as strings
        )

    fake.download_pr_metadata = download_pr_metadata

    def get_pr_comments(pr_number, comment_id):
        return [f"thread_comment-{pr_number}"]

    fake.get_pr_comments = get_pr_comments

    def get_context_from_external_issues_references(closing_issues, closing_issue_numbers, body, review_comments, review_threads, thread_comments):
        # append context marker so we can verify the returned Issue.closing_issues
        return closing_issues + [f"context-for-{closing_issue_numbers[0]}"]

    fake.get_context_from_external_issues_references = get_context_from_external_issues_references

    return fake


def test_get_converted_issues_raises_on_empty_issue_numbers():
    fake = make_fake_self()
    with pytest.raises(ValueError, match="Unspecified issue numbers"):
        ForgejoPRHandler.get_converted_issues(fake, issue_numbers=None)


def test_get_converted_issues_processes_and_skips_prs(monkeypatch):
    # Prepare PRs: two should be skipped, two valid PRs with 'number' and 'title'
    all_prs = [
        {"number": None, "title": "NoNumber"},  # should be skipped (number is None)
        {"number": 5, "title": None},  # should be skipped (title is None)
        {"number": "10", "title": "Fix bug", "body": None, "head": {"ref": "feature-branch"}},
        {"number": "20", "title": "Add feature", "body": "Body text", "head": {"ref": "main"}},
    ]

    fake = make_fake_self()

    # Patch httpx.get used inside the method to return our fake response
    fake_response = make_fake_response(all_prs)
    monkeypatch.setattr(httpx, "get", lambda url, headers: fake_response)

    # Call method with issue_numbers matching the two valid PRs (10 and 20)
    converted = ForgejoPRHandler.get_converted_issues(fake, issue_numbers=[10, 20], comment_id=123)

    # We expect two converted issues (the two valid PRs); the two invalid ones are skipped
    assert isinstance(converted, list)
    assert len(converted) == 2

    # Find issues by number for assertions
    by_number = {issue.number: issue for issue in converted}
    assert 10 in by_number and 20 in by_number

    issue10 = by_number[10]
    assert isinstance(issue10, Issue)
    assert issue10.owner == fake.owner
    assert issue10.repo == fake.repo
    assert issue10.number == 10
    assert issue10.title == "Fix bug"
    # body for PR 10 was None, so it should be empty string
    assert issue10.body == ""
    # closing_issues should include the context appended in our fake get_context_from_external_issues_references
    assert issue10.closing_issues == ["closing-10", "context-for-110"]
    # review comments/threads/thread_ids and head_branch/thread_comments should match values returned by fake methods
    assert issue10.review_comments == [f"review_comment-10"]
    # review_threads should contain objects with the structure from download_pr_metadata
    assert issue10.review_threads is not None and len(issue10.review_threads) == 1
    assert getattr(issue10.review_threads[0], "comment") == "rt-10"
    assert getattr(issue10.review_threads[0], "files") == ["file-10"]
    assert issue10.thread_ids == ["1010"]
    assert issue10.head_branch == "feature-branch"
    assert issue10.thread_comments == [f"thread_comment-10"]

    issue20 = by_number[20]
    assert issue20.title == "Add feature"
    assert issue20.body == "Body text"
    assert issue20.head_branch == "main"
    assert issue20.review_comments == [f"review_comment-20"]
    assert issue20.review_threads is not None and len(issue20.review_threads) == 1
    assert getattr(issue20.review_threads[0], "comment") == "rt-20"
    assert getattr(issue20.review_threads[0], "files") == ["file-20"]
    assert issue20.thread_comments == [f"thread_comment-20"]
    assert issue20.thread_ids == ["1020"]
    # closing issues context appended properly
    assert issue20.closing_issues == ["closing-20", "context-for-120"]
