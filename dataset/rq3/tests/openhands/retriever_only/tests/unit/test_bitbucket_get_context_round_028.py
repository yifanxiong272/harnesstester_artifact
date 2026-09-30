import re
import types
import httpx
import pytest

from openhands.resolver.interfaces.bitbucket import (
    BitbucketIssueHandler,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        # simulate successful status
        return None

    def json(self):
        return self._data


def _digit_extract(s: str) -> list[int]:
    # deterministic, simple fake of extract_issue_references: returns all ints found
    return [int(m) for m in re.findall(r"\d+", s)]


def test_get_context_all_sources_and_successful_http_round_028(monkeypatch):
    """Exercise issue_body, review_comments, review_threads and thread_comments paths and
    a mix of successful HTTP, empty issue content and an HTTP error.

    - extract_issue_references is patched to deterministically return integers found in text
    - httpx.get is patched to return a FakeResponse or raise HTTPError for specific ids

    Expected: only issues with non-empty 'raw' content are appended; HTTPError is caught
    and does not raise.
    """
    # Prepare handler and ensure necessary attributes exist
    handler = BitbucketIssueHandler("owner", "repo", "token", "user", "bitbucket.local")
    # Overwrite to deterministic values regardless of __init__ internals
    handler.base_url = "https://api.bitbucket.org/2.0"
    handler.owner = "owner"
    handler.repo = "repo"
    handler.headers = {"Authorization": "token dummy"}

    # Patch the module-level extractor used by the function under test
    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.extract_issue_references",
        _digit_extract,
    )

    # Map URLs ending with these digits to behaviors:
    # - 101 -> valid issue with non-empty raw -> should be appended
    # - 103 -> valid response but empty raw -> should NOT be appended
    # - 104 -> httpx.HTTPError raised -> should be caught and logged
    def fake_get(url, headers=None):
        if url.endswith("/101"):
            return FakeResponse({"content": {"raw": "body for 101"}})
        if url.endswith("/103"):
            return FakeResponse({"content": {"raw": ""}})
        if url.endswith("/104"):
            # simulate a network/HTTP error
            raise httpx.HTTPError("not found")
        return FakeResponse({"content": {"raw": "unknown"}})

    monkeypatch.setattr("openhands.resolver.interfaces.bitbucket.httpx.get", fake_get)

    # Inputs that produce references 101,102,103,104 (102 will be excluded by closing_issue_numbers)
    issue_body = "refs 101 102"
    review_comments = ["also refs 102"]
    review_threads = [types.SimpleNamespace(comment="thread refs 103"), types.SimpleNamespace(comment="thread refs 101")]
    thread_comments = ["thread comment 104"]

    closing_issues = ["existing"]
    closing_issue_numbers = [102]  # exclude 102 from network fetches

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # Only 101 had non-empty 'raw' and should have been appended. 103 had empty raw; 104 raised HTTPError.
    assert result == ["existing", "body for 101"], "Returned closing_issues should include appended body for 101 only"


def test_get_context_no_issue_body_and_http_error_for_thread_comment_round_028(monkeypatch):
    """Cover the branch where issue_body is falsy and review_comments/review_threads are falsy,
    and a thread_comments value leads to an HTTP error that should be caught.
    """
    handler = BitbucketIssueHandler("o", "r", "t", "u", "bitbucket.local")
    handler.base_url = "https://api.bitbucket.org/2.0"
    handler.owner = "o"
    handler.repo = "r"
    handler.headers = {"Authorization": "token dummy"}

    # extractor returns the digits found in the single thread comment -> 999
    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.extract_issue_references",
        _digit_extract,
    )

    def fake_get_error(url, headers=None):
        raise httpx.HTTPError("timeout")

    monkeypatch.setattr("openhands.resolver.interfaces.bitbucket.httpx.get", fake_get_error)

    # No issue_body, no review_comments, no review_threads; only thread_comments contains a reference
    issue_body = ""  # falsy -> skip first branch
    review_comments = None  # falsy
    review_threads = None  # falsy
    thread_comments = ["ticket-999"]

    closing_issues = []
    closing_issue_numbers = []

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # HTTP error should be caught; no body appended
    assert result == [], "On HTTPError during fetch, closing_issues should remain unchanged and no exception propagated"
