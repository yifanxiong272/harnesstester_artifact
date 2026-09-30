import types
import httpx
import pytest

import openhands.resolver.interfaces.forgejo as forgejo_mod
from openhands.resolver.interfaces.forgejo import ForgejoIssueHandler


def test_issue_body_fetch_appends_body_round_031(monkeypatch):
    """If issue_body yields an external reference, the handler should fetch
    that issue and append the returned body when non-empty.
    """
    handler = ForgejoIssueHandler("owner", "repo", "token", "user", "domain")
    # Ensure the instance has headers and a predictable download URL
    handler.headers = {"Authorization": "token"}
    handler.get_download_url = lambda: "http://download"

    # make extract_issue_references deterministic: any non-empty body -> [42]
    monkeypatch.setattr(forgejo_mod, "extract_issue_references", lambda s: [42] if s else [])

    recorded = {}

    def fake_get(url, headers):
        recorded["url"] = url
        recorded["headers"] = headers

        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"body": "fetched body"}

        return Resp()

    # Patch httpx.get used inside the module
    monkeypatch.setattr(forgejo_mod.httpx, "get", fake_get)

    closing = []
    # closing_issue_numbers doesn't include 42 so it should be fetched
    result = handler.get_context_from_external_issues_references(
        closing_issues=closing,
        closing_issue_numbers=[1],
        issue_body="some body",
        review_comments=None,
        review_threads=[],
        thread_comments=None,
    )

    # same object returned
    assert result is closing
    # fetched body appended
    assert "fetched body" in result
    # httpx.get was called with correct url and headers
    assert recorded["url"] == "http://download/42"
    assert recorded["headers"] == handler.headers


def test_multiple_sources_and_errors_round_031(monkeypatch):
    """Cover review_comments, review_threads, thread_comments loops and error handling.

    - Different input sources produce a set of unique issue ids.
    - One id returns a non-empty body and should be appended.
    - One id returns an empty body and should not be appended.
    - One id causes httpx.HTTPError and should trigger logger.warning.
    """
    handler = ForgejoIssueHandler("owner", "repo", "token", "user", "domain")
    handler.headers = {"Authorization": "token"}
    handler.get_download_url = lambda: "http://download"

    # map specific input strings to deterministic issue id lists
    def fake_extract(s):
        mapping = {
            "issue_body": [100, 200],
            "comment1": [100],
            "thread_comment1": [300],
            "thread_obj.comment": [400],
        }
        return mapping.get(s, [])

    monkeypatch.setattr(forgejo_mod, "extract_issue_references", fake_extract)

    warnings = []

    # capture logger.warning calls
    monkeypatch.setattr(forgejo_mod.logger, "warning", lambda msg: warnings.append(msg))

    def fake_get(url, headers):
        num = int(url.rsplit("/", 1)[1])

        class Resp:
            def __init__(self, body):
                self._body = body

            def raise_for_status(self):
                return None

            def json(self):
                return {"body": self._body}

        if num == 100:
            return Resp("body100")
        if num == 300:
            return Resp("")
        if num == 400:
            # simulate remote error
            raise httpx.HTTPError("boom")
        raise AssertionError(f"Unexpected issue fetch for {num}")

    monkeypatch.setattr(forgejo_mod.httpx, "get", fake_get)

    review_thread = types.SimpleNamespace(comment="thread_obj.comment")
    closing = []

    result = handler.get_context_from_external_issues_references(
        closing_issues=closing,
        closing_issue_numbers=[200],
        issue_body="issue_body",
        review_comments=["comment1"],
        review_threads=[review_thread],
        thread_comments=["thread_comment1"],
    )

    # 100 -> body100 should be appended
    assert "body100" in result
    # 300 returned empty body -> should not have an empty string appended
    assert "" not in result
    # 400 raised HTTPError -> logger.warning should have been called mentioning issue 400
    assert any("Failed to fetch issue 400" in str(w) or "issue 400" in str(w) for w in warnings)
