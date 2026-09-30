# file: openhands/resolver/interfaces/azure_devops.py:321-434
# asked: {"lines": [325, 327, 330, 331, 332, 334, 335, 337, 339, 340, 342, 343, 344, 347, 350, 351, 352, 353, 356, 357, 358, 359, 360, 362, 363, 364, 365, 366, 369, 370, 372, 373, 375, 376, 377, 379, 380, 384, 385, 387, 389, 390, 392, 394, 395, 396, 397, 399, 402, 403, 404, 405, 408, 409, 410, 411, 412, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 432, 434], "branches": [[325, 327], [325, 330], [331, 332], [331, 339], [340, 342], [340, 434], [356, 357], [356, 369], [357, 356], [357, 360], [364, 365], [364, 366], [369, 370], [369, 417], [394, 395], [394, 417], [403, 404], [403, 408], [408, 394], [408, 409]]}
# gained: {"lines": [325, 327, 330, 331, 332, 334, 335, 337, 339, 340, 342, 343, 344, 347, 350, 351, 352, 353, 356, 357, 358, 359, 360, 362, 363, 364, 365, 366, 369, 370, 372, 373, 375, 376, 377, 379, 380, 384, 385, 387, 389, 390, 392, 394, 395, 396, 397, 399, 402, 403, 404, 405, 408, 409, 410, 411, 412, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 432, 434], "branches": [[325, 327], [325, 330], [331, 332], [331, 339], [340, 342], [340, 434], [356, 357], [356, 369], [357, 360], [364, 365], [369, 370], [369, 417], [394, 395], [394, 417], [403, 404], [403, 408], [408, 394], [408, 409]]}

import pytest

from openhands.resolver.interfaces.azure_devops import AzureDevOpsIssueHandler
from openhands.resolver.interfaces.issue import Issue, ReviewThread

class _ResponseMock:
    def __init__(self, json_data):
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        # Simulate a successful response
        return None

def test_get_converted_issues_all_non_pr(monkeypatch):
    """
    Test the branch where issue_numbers is None and the work item is NOT a PR.
    Ensures fields, thread comments and absence of PR-related fields are handled.
    """
    handler = AzureDevOpsIssueHandler(token="t", organization="org", project="proj", repository="repo")

    # Prepare a non-PR work item returned by download_issues
    work_item = {
        "id": 101,
        "fields": {
            "System.Title": "Test Issue",
            "System.Description": "Issue description"
        },
        "relations": []  # no PR relations
    }

    # Patch download_issues to return our work_item
    monkeypatch.setattr(handler, "download_issues", lambda: [work_item])

    # Patch get_issue_comments to return some thread comments
    monkeypatch.setattr(handler, "get_issue_comments", lambda issue_number, comment_id=None: ["first comment", "second comment"])

    # Call the method
    issues = handler.get_converted_issues()

    # Assertions
    assert isinstance(issues, list)
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.number == 101
    assert issue.title == "Test Issue"
    assert issue.body == "Issue description"
    assert issue.thread_comments == ["first comment", "second comment"]
    assert issue.review_comments is None
    assert issue.review_threads is None
    assert issue.head_branch is None
    assert issue.base_branch is None

def test_get_converted_issues_specific_pr_issue(monkeypatch):
    """
    Test the branch where a specific issue number is provided and the work item links
    to a pull request. This should exercise PR fetching, threads parsing including file paths.
    """
    handler = AzureDevOpsIssueHandler(token="t", organization="org", project="proj", repository="repo")

    # Ensure headers callable used by code exists
    monkeypatch.setattr(handler, "get_headers", lambda: {"Authorization": "Bearer t"})

    # Patch get_issue_comments to return no top-level thread comments for PR
    monkeypatch.setattr(handler, "get_issue_comments", lambda issue_number, comment_id=None: [])

    # Prepare the work item JSON that includes a relation to a PR.
    # The relation URL intentionally contains both 'pullrequest' (lowercase) and
    # 'pullRequests/NUMBER' (camelCase) so the implementation's checks succeed.
    pr_number = 42
    work_item = {
        "id": 202,
        "fields": {
            "System.Title": "PR-linked Work Item",
            "System.Description": "Work item that links a PR"
        },
        "relations": [
            {
                "rel": "ArtifactLink",
                "url": f"https://example/pullrequest/info/and/pullRequests/{pr_number}"
            }
        ],
    }

    # Prepare PR details response
    pr_data = {
        "sourceRefName": "refs/heads/feature-branch",
        "targetRefName": "refs/heads/main"
    }

    # Prepare threads response with two threads:
    # - one with comments and a file path
    # - one with comments and no file path
    threads_data = {
        "value": [
            {
                "comments": [{"content": "Review comment 1"}, {"content": "Review comment 2"}],
                "threadContext": {"filePath": "/src/file1.py"}
            },
            {
                "comments": [{"content": "Another comment"}],
                "threadContext": {}  # no filePath
            },
            # include an empty thread to ensure it's ignored when no comments
            {
                "comments": [],
                "threadContext": {"filePath": "/src/ignored.py"}
            }
        ]
    }

    # Create a mapping from URL substrings to response payloads
    def _httpx_get_mock(url, headers=None):
        # workitem fetch URLs contain '/wit/workitems/'
        if "/wit/workitems/" in url:
            return _ResponseMock(work_item)
        # PR details fetch: repo_api_url + '/pullRequests/{pr_number}?api-version=7.1'
        if f"/pullRequests/{pr_number}?" in url and "/threads" not in url:
            return _ResponseMock(pr_data)
        # Threads fetch
        if f"/pullRequests/{pr_number}/threads" in url:
            return _ResponseMock(threads_data)
        # Default unexpected - return empty structure
        return _ResponseMock({})

    # Patch httpx.get used by the implementation
    import httpx
    monkeypatch.setattr(httpx, "get", _httpx_get_mock)

    # Call method with specific issue number (the handler will fetch workitem for this id)
    issues = handler.get_converted_issues(issue_numbers=[pr_number])

    # Assertions about the returned Issue
    assert isinstance(issues, list)
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    # Basic fields
    assert issue.number == 202
    assert issue.title == "PR-linked Work Item"
    assert issue.body == "Work item that links a PR"
    # Top-level thread_comments returned by get_issue_comments (we patched to empty list)
    assert issue.thread_comments == []
    # PR-related fields should be populated
    assert issue.head_branch == "feature-branch"
    assert issue.base_branch == "main"
    # review_comments should contain all comments from threads (in order)
    assert issue.review_comments == ["Review comment 1", "Review comment 2", "Another comment"]
    # review_threads should be list of ReviewThread for threads that had comments
    assert isinstance(issue.review_threads, list)
    # There should be two review threads (the one with two comments and the one with one comment)
    assert len(issue.review_threads) == 2
    # Validate contents of first thread
    first_thread = issue.review_threads[0]
    assert isinstance(first_thread, ReviewThread)
    assert first_thread.comment == "Review comment 1\nReview comment 2"
    assert first_thread.files == ["/src/file1.py"]
    # Validate contents of second thread
    second_thread = issue.review_threads[1]
    assert second_thread.comment == "Another comment"
    assert second_thread.files == []
