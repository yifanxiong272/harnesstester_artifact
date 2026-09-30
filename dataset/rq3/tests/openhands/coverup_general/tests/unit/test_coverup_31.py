# file: openhands/resolver/interfaces/forgejo.py:427-487
# asked: {"lines": [430, 431, 433, 434, 435, 437, 438, 439, 440, 441, 444, 445, 446, 447, 448, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 462, 463, 464, 465, 466, 467, 468, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 485, 487], "branches": [[430, 431], [430, 433], [445, 446], [445, 487], [446, 447], [446, 450]]}
# gained: {"lines": [430, 431, 433, 434, 435, 437, 438, 439, 440, 441, 444, 445, 446, 447, 448, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 462, 463, 464, 465, 466, 467, 468, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 485, 487], "branches": [[430, 431], [430, 433], [445, 446], [445, 487], [446, 447], [446, 450]]}

import pytest

import openhands.resolver.interfaces.forgejo as forgejo_mod
from openhands.resolver.interfaces.forgejo import ForgejoPRHandler
from openhands.resolver.interfaces.issue import Issue


class DummyResponse:
    def __init__(self, data):
        self._data = data
        self.raise_called = False

    def raise_for_status(self):
        # simulate a successful response
        self.raise_called = True
        return None

    def json(self):
        return self._data


def test_get_converted_issues_raises_on_empty_issue_numbers():
    handler = ForgejoPRHandler("owner", "repo", "token")
    # ensure _to_int exists and behaves
    handler._to_int = lambda x: int(x) if x is not None else 0

    with pytest.raises(ValueError) as exc:
        handler.get_converted_issues([])
    assert "Unspecified issue numbers" in str(exc.value)


def test_get_converted_issues_filters_and_converts(monkeypatch):
    handler = ForgejoPRHandler("ownerX", "repoY", "tokenZ")
    # make sure _to_int is simple and deterministic
    handler._to_int = lambda x: int(x) if x is not None else 0

    # Prepare PRs:
    # - pr_good should be converted
    # - pr_missing_title should be skipped (has number but missing title)
    # - pr_not_requested should be filtered out by number/index
    pr_good = {
        "number": 1,
        "title": "Good PR",
        "body": "This PR closes #10",
        "head": {"ref": "feature/awesome"},
    }
    pr_missing_title = {
        "number": 2,
        "title": None,  # will trigger skipping in code
        "body": "No title here",
        "head": {"ref": "feature/bad"},
    }
    pr_not_requested = {
        "index": 3,
        "title": "Not Requested",
        "body": "Should be filtered out",
        "head": {"ref": "feature/other"},
    }
    all_prs = [pr_good, pr_missing_title, pr_not_requested]

    captured_get = {}

    def fake_httpx_get(url, headers=None):
        # record that the correct url/headers were provided
        captured_get["url"] = url
        captured_get["headers"] = headers
        return DummyResponse(all_prs)

    # Patch httpx.get used in the module
    monkeypatch.setattr(forgejo_mod.httpx, "get", fake_httpx_get)

    # Prepare download_pr_metadata to assert it receives pr_number and comment_id
    called = {"download_args": None, "get_comments_args": None, "context_args": None}

    def fake_download_pr_metadata(pr_number, comment_id):
        called["download_args"] = (pr_number, comment_id)
        # return closing_issues, closing_issue_numbers, review_comments, review_threads, thread_ids
        return (["ext-issue"], [10], ["rev comment"], [], ["thread-1"])

    def fake_get_pr_comments(pr_number, comment_id):
        called["get_comments_args"] = (pr_number, comment_id)
        return ["thread comment 1"]

    def fake_get_context_from_external_issues_references(
        closing_issues, closing_issue_numbers, issue_body, review_comments, review_threads, thread_comments
    ):
        called["context_args"] = (
            list(closing_issues),
            list(closing_issue_numbers),
            issue_body,
            list(review_comments) if review_comments is not None else None,
            list(review_threads) if review_threads is not None else None,
            list(thread_comments) if thread_comments is not None else None,
        )
        # simulate augmenting closing issues
        return closing_issues + ["augmented-context"]

    # Monkeypatch instance methods
    handler.download_pr_metadata = fake_download_pr_metadata
    handler.get_pr_comments = fake_get_pr_comments
    handler.get_context_from_external_issues_references = fake_get_context_from_external_issues_references

    # Call with issue_numbers that should include pr_good (1) and pr_missing_title (2)
    converted = handler.get_converted_issues([1, 2], comment_id=777)

    # Assertions:
    # - httpx.get was called with the handler's download_url and headers attribute
    assert captured_get["url"] == handler.download_url
    assert captured_get["headers"] == getattr(handler, "headers")

    # - download_pr_metadata and get_pr_comments were called for pr_good only (pr_missing_title is skipped later)
    assert called["download_args"] == (1, 777)
    assert called["get_comments_args"] == (1, 777)

    # - context function was called with expected arguments (closing issues, numbers, body, review comments, threads, thread comments)
    expected_context_args = (
        ["ext-issue"],
        [10],
        pr_good["body"],
        ["rev comment"],
        [],
        ["thread comment 1"],
    )
    assert called["context_args"] == expected_context_args

    # - Only pr_good should have been converted (pr_missing_title skipped, pr_not_requested filtered out)
    assert isinstance(converted, list)
    assert len(converted) == 1

    issue: Issue = converted[0]
    # verify the issue fields correspond to what the handler created
    assert issue.owner == "ownerX"
    assert issue.repo == "repoY"
    assert issue.number == 1
    assert issue.title == "Good PR"
    assert issue.body == pr_good["body"]
    # closing_issues should be the result of fake_get_context_from_external_issues_references
    assert issue.closing_issues == ["ext-issue", "augmented-context"]
    # review_comments, review_threads, thread_ids, head_branch, thread_comments coming from our fakes/pr
    assert issue.review_comments == ["rev comment"]
    assert issue.review_threads == []  # we returned empty list
    assert issue.thread_ids == ["thread-1"]
    assert issue.head_branch == "feature/awesome"
    assert issue.thread_comments == ["thread comment 1"]
