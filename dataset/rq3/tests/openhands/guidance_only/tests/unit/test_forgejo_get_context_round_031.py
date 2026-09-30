import httpx
from types import SimpleNamespace
import pytest

import openhands.resolver.interfaces.forgejo as forgejo


def test_get_context_mixed_inputs_round_031(monkeypatch):
    """Exercise branches where issue_body, review_comments, review_threads and thread_comments
    produce several referenced issue numbers. Some HTTP fetches return bodies, one raises HTTPError.

    Expected behavior:
    - Only referenced issue numbers not present in closing_issue_numbers are fetched.
    - Responses with a non-empty 'body' are appended to closing_issues.
    - HTTP errors are caught and a warning is logged; function continues.
    """
    # Prepare a handler instance and ensure get_download_url and headers exist
    handler = forgejo.ForgejoIssueHandler("owner", "repo", "token", "user", "domain")
    handler.get_download_url = lambda: "http://download"
    handler.headers = {"Authorization": "token"}

    # Controlled mapping for extract_issue_references so we know which ids will be returned for each input
    def fake_extract_issue_references(value):
        mapping = {
            "issue-body": [101, 200],
            "review-1": [300],
            "thread-comment": [400],
            "thread-comment-2": [201],
        }
        return mapping.get(value, [])

    monkeypatch.setattr(forgejo, "extract_issue_references", fake_extract_issue_references)

    # Capture logger.warning calls
    logged = []

    def fake_warning(msg):
        logged.append(msg)

    monkeypatch.setattr(forgejo.logger, "warning", fake_warning)

    # Implement httpx.get to return different responses depending on the issue number in the URL
    def fake_httpx_get(url, headers=None):
        # parse last path segment as the issue number
        num = int(str(url).rsplit("/", 1)[-1])

        # Simulate an HTTP error for issue 201
        if num == 201:
            raise httpx.HTTPError("boom")

        class Resp:
            def raise_for_status(self):
                return None

            def json(self_inner):
                # Only issues 200 and 400 have bodies; 300 has empty body
                if num in (200, 400):
                    return {"body": f"body{num}"}
                return {"body": ""}

        return Resp()

    monkeypatch.setattr(forgejo.httpx, "get", fake_httpx_get)

    closing_issues = ["existing"]
    closing_issue_numbers = [101]  # 101 should be filtered out from references

    res = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body="issue-body",
        review_comments=["review-1"],
        review_threads=[SimpleNamespace(comment="thread-comment")],
        thread_comments=["thread-comment-2"],
    )

    # We expect bodies from issue 200 and 400 to be appended; 300 had empty body, 201 raised HTTPError
    assert res[0] == "existing"
    assert set(res[1:]) == {"body200", "body400"}

    # Ensure the HTTP error was logged mentioning issue 201
    assert any("Failed to fetch issue 201" in str(msg) for msg in logged)


def test_get_context_no_unique_ids_round_031(monkeypatch):
    """If all extracted references are already present in closing_issue_numbers, no HTTP calls
    should be performed and the closing_issues list should be returned unchanged.
    """
    handler = forgejo.ForgejoIssueHandler("o", "r", "t", "u", "d")
    handler.get_download_url = lambda: "http://download"
    handler.headers = {"X": "Y"}

    # Always return a reference that is already in closing_issue_numbers
    monkeypatch.setattr(forgejo, "extract_issue_references", lambda v: [1])

    # If httpx.get is invoked, fail the test to ensure no network fetch is attempted
    def fail_get(*a, **k):
        raise AssertionError("httpx.get should not be called when there are no unique ids")

    monkeypatch.setattr(forgejo.httpx, "get", fail_get)

    closing_issues = ["already"]
    closing_issue_numbers = [1]

    res = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body="something",
        review_comments=None,
        review_threads=[],
        thread_comments=None,
    )

    assert res == ["already"]
