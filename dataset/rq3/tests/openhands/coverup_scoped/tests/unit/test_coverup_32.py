# file: openhands/resolver/interfaces/bitbucket.py:353-411
# asked: {"lines": [375, 377, 378, 380, 381, 382, 384, 385, 386, 387, 390, 391, 392, 394, 395, 396, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 411], "branches": [[377, 378], [377, 380], [380, 381], [380, 384], [381, 382], [381, 384], [384, 385], [384, 390], [385, 386], [385, 390], [390, 391], [390, 394], [391, 392], [391, 394], [399, 400], [399, 411], [406, 399], [406, 407]]}
# gained: {"lines": [375, 377, 378, 380, 381, 382, 384, 385, 386, 387, 390, 391, 392, 394, 395, 396, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 411], "branches": [[377, 378], [380, 381], [380, 384], [381, 382], [381, 384], [384, 385], [384, 390], [385, 386], [385, 390], [390, 391], [390, 394], [391, 392], [391, 394], [399, 400], [399, 411], [406, 407]]}

import httpx
import pytest

from types import SimpleNamespace


def _get_module():
    # Lazy import inside helper to avoid import-time side effects in test collection
    import openhands.resolver.interfaces.bitbucket as mod
    return mod


def _make_handler():
    mod = _get_module()
    return mod.BitbucketIssueHandler("owner", "repo", "token")


def test_get_context_from_external_issues_references_success(monkeypatch):
    mod = _get_module()

    # capture calls to httpx.get
    calls = []

    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": {"raw": "fetched body for issue"}}  # body to be appended

    def fake_get(url, headers=None):
        calls.append((url, headers))
        return DummyResp()

    # Make extract_issue_references always return [5], so only one external issue is processed
    monkeypatch.setattr(mod, "extract_issue_references", lambda _text: [5])
    monkeypatch.setattr(mod.httpx, "get", fake_get)

    handler = _make_handler()

    # Provide values for all branches: issue_body, review_comments, review_threads, thread_comments
    review_thread_obj = SimpleNamespace(comment="rt comment")
    closing_issues = ["initial body"]
    returned = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues,
        closing_issue_numbers=[],
        issue_body="issue body text",
        review_comments=["review comment"],
        review_threads=[review_thread_obj],
        thread_comments=["thread comment"],
    )

    # The fetched issue body should have been appended
    assert "fetched body for issue" in returned
    # Ensure httpx.get was called for issue number 5 and headers were passed
    assert calls, "httpx.get was not called"
    url_called, headers_used = calls[0]
    assert "/repositories/owner/repo/issues/5" in url_called
    assert headers_used == handler.headers


def test_get_context_from_external_issues_references_http_error_logs_warning(monkeypatch):
    mod = _get_module()

    # make extract_issue_references return a single issue number 6
    monkeypatch.setattr(mod, "extract_issue_references", lambda _text: [6])

    # fake httpx.get to raise an HTTPError
    def fake_get_raise(url, headers=None):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(mod.httpx, "get", fake_get_raise)

    # capture logger.warning calls
    logged = {}

    def fake_warning(msg):
        # store the last warning message
        logged["msg"] = msg

    monkeypatch.setattr(mod.logger, "warning", fake_warning)

    handler = _make_handler()
    closing_issues = []
    returned = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues,
        closing_issue_numbers=[],
        issue_body="body that references #6",
        review_comments=None,
        review_threads=None,
        thread_comments=None,
    )

    # Nothing should have been appended because the GET raised an HTTPError
    assert returned == [], "closing_issues should remain empty on HTTP error"
    # Logger should have been called with a message mentioning the issue number
    assert "Failed to fetch issue 6" in logged.get("msg", "")
