import types
from types import SimpleNamespace
import httpx
import pytest

import openhands.resolver.interfaces.bitbucket as bitbucket_module
from openhands.resolver.interfaces.bitbucket import BitbucketIssueHandler


class _FakeResponse:
    def __init__(self, json_data=None, exc=None):
        self._json = json_data or {}
        self._exc = exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._json


def test_get_context_success_round_028(monkeypatch):
    """When extract_issue_references yields integer issue numbers, the handler
    should fetch only the non-closed unique issue numbers and append the
    fetched 'raw' content to the closing_issues list."""

    # Make extract_issue_references deterministic: return ints so difference
    # against closing_issue_numbers can exclude entries
    def fake_extract(_any):
        # return duplicates across different inputs to exercise set-unique logic
        return [101, 202]

    monkeypatch.setattr(bitbucket_module, "extract_issue_references", fake_extract)

    captured = {"urls": []}

    def fake_get(url, headers=None):
        # record requested URL for later assertion
        captured["urls"].append((url, headers))
        return _FakeResponse(json_data={"content": {"raw": "fetched body for 101"}})

    # Patch the httpx.get used inside the module under test
    monkeypatch.setattr(bitbucket_module.httpx, "get", fake_get)

    # Create a handler and ensure base_url/owner/repo/headers are present
    handler = BitbucketIssueHandler("ownerx", "repoy", "token", "user", "example.com")
    # constructor may set these, but ensure deterministic values used by URL
    handler.base_url = "https://bitbucket.example"
    handler.owner = "ownerx"
    handler.repo = "repoy"
    handler.headers = {"Authorization": "Bearer tok"}

    # Start with an existing closing issue body and mark 202 as already closed.
    closing_issues = ["existing-body"]
    closing_issue_numbers = [202]

    # Provide inputs on all branches: issue_body, review_comments, review_threads, thread_comments
    issue_body = "issue body text"
    review_comments = ["review comment"]
    review_threads = [SimpleNamespace(comment="thread comment")]
    thread_comments = ["thread comment 2"]

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # The function returns the same list object with fetched contents appended.
    assert result is closing_issues

    # The only unique, non-closed issue number from the fake_extract results is 101
    assert any("/repositories/ownerx/repoy/issues/101" in u[0] for u in captured["urls"])

    # The fetched issue body should have been appended
    assert any("fetched body for 101" in s for s in result)


def test_get_context_http_error_round_028(monkeypatch):
    """If fetching an external issue raises httpx.HTTPError, the handler should
    catch it and log a warning, and not append any fetched body to the
    closing_issues list."""

    # Return a single integer issue number to fetch
    monkeypatch.setattr(bitbucket_module, "extract_issue_references", lambda _s: [303])

    # Make httpx.get return a response whose raise_for_status raises httpx.HTTPError
    def fake_get_error(url, headers=None):
        return _FakeResponse(json_data={"content": {"raw": "should not be used"}}, exc=httpx.HTTPError("boom"))

    monkeypatch.setattr(bitbucket_module.httpx, "get", fake_get_error)

    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    # Patch the module logger's warning to capture the message
    monkeypatch.setattr(bitbucket_module, "logger", types.SimpleNamespace(warning=fake_warning))

    handler = BitbucketIssueHandler("ownerA", "repoB", "token", "user", "example.com")
    handler.base_url = "https://bitbucket.example"
    handler.owner = "ownerA"
    handler.repo = "repoB"
    handler.headers = {}

    closing_issues = ["orig"]

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        [],  # no closed numbers so 303 will be attempted
        None,  # no issue_body
        None,  # no review_comments
        [],  # no review_threads
        None,  # no thread_comments
    )

    # No new bodies appended because fetch raised
    assert result == ["orig"]

    # Warning should have been logged and mentions the issue number
    assert any("303" in str(m) or "issue 303" in str(m) for m in warnings)
