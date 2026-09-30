import re
import types
import pytest

from openhands.resolver.interfaces.azure_devops import (
    AzureDevOpsIssueHandler,
    Issue,
    ReviewThread,
)


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        # Simulate always-successful status
        return None

    def json(self):
        return self._data


def test_get_converted_issues_download_all_round_009():
    # Setup handler and patch download_issues and get_issue_comments
    handler = AzureDevOpsIssueHandler(token="t", organization="org", project="proj", repository="repo")

    # Work item without PR relations
    work_item = {
        "id": 1,
        "fields": {"System.Title": "Title 1", "System.Description": "Desc 1"},
        "relations": [],
    }

    # Patch methods on the instance deterministically
    handler.download_issues = lambda: [work_item]
    handler.get_issue_comments = lambda issue_number, comment_id=None: ["thread comment 1", "thread comment 2"]

    # Call the method under test
    issues = handler.get_converted_issues()

    # Assertions: ensure a single Issue created and fields set as expected when not a PR
    assert isinstance(issues, list) and len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.number == 1
    assert issue.title == "Title 1"
    assert issue.body == "Desc 1"
    # thread_comments come from get_issue_comments
    assert issue.thread_comments == ["thread comment 1", "thread comment 2"]
    # Not a PR -> no review comments or threads
    assert issue.review_comments is None
    assert issue.review_threads is None
    assert issue.head_branch is None and issue.base_branch is None


def test_get_converted_issues_with_pr_round_009(monkeypatch):
    # Setup handler with explicit api urls so we can detect them in the httpx.get stub
    handler = AzureDevOpsIssueHandler(token="t", organization="org", project="proj", repository="repo")
    handler.work_items_api_url = "https://dev.azure.com/org/project/_apis"
    handler.repo_api_url = "https://dev.azure.com/org/project/_apis/git/repositories/repo"

    # Ensure get_headers returns a deterministic mapping expected by the code
    handler.get_headers = lambda: {"Authorization": "Basic ZHVtbXk="}

    # get_issue_comments should be called for the work item and we simulate no thread comments there
    handler.get_issue_comments = lambda issue_number, comment_id=None: []

    # Prepare the work item that includes a relation referencing a pull request
    work_item_pr = {
        "id": 42,
        "fields": {"System.Title": "PR Title", "System.Description": "PR Desc"},
        "relations": [
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///Git/PullRequestId/pullRequests/42",
            }
        ],
    }

    # PR data response: contains refs with 'refs/heads/' prefix that should be stripped
    pr_data = {
        "sourceRefName": "refs/heads/feature/xyz",
        "targetRefName": "refs/heads/main",
    }

    # Threads response: one thread with two comments and a file path in threadContext
    threads_response = {"value": [
        {
            "comments": [{"content": "c1"}, {"content": "c2"}],
            "threadContext": {"filePath": "/src/file.py"},
        }
    ]}

    # Stub for httpx.get that returns different DummyResponse data depending on the URL
    def fake_httpx_get(url, headers=None):
        # Work item fetch
        if "workitems/42" in url:
            return DummyResponse(work_item_pr)
        # Pull request fetch
        if re.search(r"/pullRequests/42\?", url):
            return DummyResponse(pr_data)
        # Threads fetch
        if "/pullRequests/42/threads" in url:
            return DummyResponse(threads_response)
        # Fall back
        return DummyResponse({})

    # Patch httpx.get where the module resolves it
    monkeypatch.setattr("openhands.resolver.interfaces.azure_devops.httpx.get", fake_httpx_get)

    # Call the method under test: provide explicit issue_numbers to follow the alternate path
    issues = handler.get_converted_issues(issue_numbers=[42], comment_id=None)

    # Assertions
    assert isinstance(issues, list) and len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    # Basic fields
    assert issue.number == 42
    assert issue.title == "PR Title"
    assert issue.body == "PR Desc"
    # PR-specific fields
    assert issue.head_branch == "feature/xyz"
    assert issue.base_branch == "main"
    # review_comments should aggregate comments from threads
    assert issue.review_comments == ["c1", "c2"]
    # review_threads should contain a ReviewThread with joined comments and file path
    assert isinstance(issue.review_threads, list) and len(issue.review_threads) == 1
    rt = issue.review_threads[0]
    assert isinstance(rt, ReviewThread)
    assert rt.comment == "c1\nc2"
    assert rt.files == ["/src/file.py"]
