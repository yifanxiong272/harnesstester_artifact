import types
import httpx
from types import SimpleNamespace

import pytest

from openhands.resolver.interfaces.bitbucket import BitbucketIssueHandler


class _FakeResponse:
    def __init__(self, num):
        self._num = num

    def raise_for_status(self):
        # success for all by default; tests may patch httpx.get to raise explicitly
        return None

    def json(self):
        # return different raw bodies for different issue numbers
        if self._num == 456:
            return {"content": {"raw": "body456"}}
        if self._num == 789:
            return {"content": {"raw": ""}}
        if self._num == 999:
            return {"content": {"raw": "body999"}}
        return {"content": {"raw": ""}}


def test_get_context_success_round_028(monkeypatch):
    """Happy path: issue_body, review_comments, review_threads, thread_comments produce
    multiple unique references; httpx.get returns responses with some non-empty and some
    empty bodies. The function should append non-empty issue bodies to closing_issues and
    ignore empty ones."""

    handler = BitbucketIssueHandler(
        owner="owner",
        repo="repo",
        token="token",
        username="user",
        base_domain="bitbucket.org",
    )

    # Prepare inputs
    closing_issues = []
    closing_issue_numbers = [123]  # ensure 123 will be filtered out
    issue_body = "ref to #123"
    review_comments = ["ref 456"]
    review_threads = [SimpleNamespace(comment="ref 789")]
    thread_comments = ["ref 999"]

    # Map input texts to issue numbers deterministically
    mapping = {
        "ref to #123": [123],
        "ref 456": [456],
        "ref 789": [789],
        "ref 999": [999],
    }

    # Patch extract_issue_references where the module resolves it
    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.extract_issue_references",
        lambda s: mapping.get(s, []),
    )

    # Patch httpx.get used inside the target function to return controlled responses
    def _fake_get(url, headers=None):
        # last path segment is the issue number
        num = int(url.rstrip("/").split("/")[-1])
        return _FakeResponse(num)

    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.httpx.get",
        _fake_get,
    )

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # Assertions: appended non-empty bodies present; empty bodies not appended
    assert "body456" in result, "expected body456 to be appended"
    assert "body999" in result, "expected body999 to be appended"
    assert "" not in result, "empty bodies should not be appended"
    assert "body789" not in result, "body for 789 was empty and must not be present"


def test_get_context_error_round_028(monkeypatch):
    """Error path: when httpx.get raises HTTPError for a referenced issue, the code should
    catch it and call logger.warning with a message containing the issue number."""

    handler = BitbucketIssueHandler(
        owner="owner",
        repo="repo",
        token="token",
        username="user",
        base_domain="bitbucket.org",
    )

    closing_issues = []
    closing_issue_numbers = []

    # Make issue_body falsy to exercise the branch where review_comments is used
    issue_body = ""
    review_comments = ["err 321"]
    review_threads = None
    thread_comments = None

    # Map the review comment to an issue number that will cause httpx.get to raise
    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.extract_issue_references",
        lambda s: [321] if s == "err 321" else [],
    )

    # Replace httpx.get with a function that raises HTTPError for the requested issue
    def _raising_get(url, headers=None):
        raise httpx.HTTPError("simulated network failure")

    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.httpx.get",
        _raising_get,
    )

    # Capture warning calls from the module-level logger by patching its warning function
    captured = []

    def _capture_warning(msg):
        captured.append(msg)

    monkeypatch.setattr(
        "openhands.resolver.interfaces.bitbucket.logger.warning",
        _capture_warning,
    )

    # Invoke
    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # No new issue bodies should be appended on error
    assert result == closing_issues

    # Logger warning should have been called once and mention the failing issue number
    assert captured, "expected logger.warning to be called on HTTPError"
    assert any("321" in str(x) for x in captured), "warning must mention the failing issue number 321"
