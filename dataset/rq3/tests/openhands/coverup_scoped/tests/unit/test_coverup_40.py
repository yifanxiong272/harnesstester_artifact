# file: openhands/resolver/interfaces/forgejo.py:234-276
# asked: {"lines": [243, 245, 246, 248, 249, 250, 252, 253, 254, 256, 257, 258, 260, 262, 263, 264, 265, 266, 268, 269, 270, 271, 272, 273, 274, 276], "branches": [[245, 246], [245, 248], [248, 249], [248, 252], [249, 250], [249, 252], [252, 253], [252, 256], [253, 254], [253, 256], [256, 257], [256, 260], [257, 258], [257, 260], [262, 263], [262, 276], [271, 262], [271, 272]]}
# gained: {"lines": [243, 245, 246, 248, 249, 250, 252, 253, 254, 256, 257, 258, 260, 262, 263, 264, 265, 266, 268, 269, 270, 271, 272, 273, 274, 276], "branches": [[245, 246], [245, 248], [248, 249], [248, 252], [249, 250], [249, 252], [252, 253], [252, 256], [253, 254], [253, 256], [256, 257], [256, 260], [257, 258], [257, 260], [262, 263], [262, 276], [271, 272]]}

import pytest
import httpx
from types import SimpleNamespace

import importlib

forgejo_mod = importlib.import_module("openhands.resolver.interfaces.forgejo")
from openhands.resolver.interfaces.forgejo import ForgejoIssueHandler
from openhands.resolver.interfaces.issue import ReviewThread


class _MockResponse:
    def __init__(self, data=None, raise_exc: Exception | None = None):
        self._data = data or {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._data


def test_get_context_handles_success_and_http_error(monkeypatch):
    calls = []

    # fake extract_issue_references: any non-empty input yields references 10 and 20
    def fake_extract_issue_references(value):
        calls.append(("extract", value))
        if value:
            return [10, 20]
        return []

    monkeypatch.setattr(forgejo_mod, "extract_issue_references", fake_extract_issue_references)

    # capture warnings
    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    monkeypatch.setattr(forgejo_mod.logger, "warning", fake_warning)

    # fake httpx.get behavior: 10 returns body, 20 raises HTTPError
    get_calls = []

    def fake_get(url, headers=None):
        get_calls.append((url, headers))
        if url.endswith("/10"):
            return _MockResponse({"body": "body-for-10"})
        elif url.endswith("/20"):
            # simulate network or HTTP error
            raise httpx.HTTPError("simulated fetch failure for 20")
        else:
            return _MockResponse({})

    # patch the httpx.get used in the module
    monkeypatch.setattr(forgejo_mod.httpx, "get", fake_get)

    # instantiate handler and ensure get_download_url and headers are predictable
    handler = ForgejoIssueHandler("owner", "repo", "token")
    # Ensure get_download_url used during method call returns deterministic base
    monkeypatch.setattr(handler, "get_download_url", lambda: "http://example.com/issues")
    handler.headers = {"Authorization": "token"}

    # Provide inputs that trigger all extraction branches
    closing_issues_initial = ["preexisting"]
    closing_issue_numbers = []  # so both 10 and 20 are considered unique
    issue_body = "issue body"
    review_comments = ["review comment"]
    review_threads = [ReviewThread(comment="thread comment", files=[])]
    thread_comments = ["thread comment text"]

    result = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues_initial.copy(),
        closing_issue_numbers=closing_issue_numbers,
        issue_body=issue_body,
        review_comments=review_comments,
        review_threads=review_threads,
        thread_comments=thread_comments,
    )

    # Assertions:
    # - original closing issue remains
    assert "preexisting" in result
    # - body from issue 10 was appended
    assert "body-for-10" in result
    # - httpx.get was called for both issue ids
    requested_urls = [u for u, _ in get_calls]
    assert "http://example.com/issues/10" in requested_urls
    assert "http://example.com/issues/20" in requested_urls
    # - a warning was emitted for the failed fetch of 20
    assert any("Failed to fetch issue 20" in str(w) for w in warnings)


def test_get_context_no_inputs_no_calls(monkeypatch):
    # When all inputs are empty/None the function should simply return closing_issues unchanged
    # and should not call httpx.get or extract_issue_references.

    extract_called = []

    def fake_extract_issue_references(value):
        extract_called.append(value)
        return []

    monkeypatch.setattr(forgejo_mod, "extract_issue_references", fake_extract_issue_references)

    get_called = []

    def fake_get(url, headers=None):
        get_called.append((url, headers))
        return _MockResponse({"body": "should-not-be-used"})

    monkeypatch.setattr(forgejo_mod.httpx, "get", fake_get)

    handler = ForgejoIssueHandler("owner", "repo", "token")
    monkeypatch.setattr(handler, "get_download_url", lambda: "http://example.com/issues")
    handler.headers = {"Authorization": "token"}

    closing_issues_initial = ["only"]
    result = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues_initial.copy(),
        closing_issue_numbers=[1, 2],
        issue_body="",
        review_comments=None,
        review_threads=[],
        thread_comments=None,
    )

    # No extraction should have been called for empty inputs
    # extract_issue_references might not be called at all (or might be called with empty strings depending on code paths),
    # ensure httpx.get was never called.
    assert get_called == []
    # And the result should equal the initial list (no additions)
    assert result == ["only"]
