import httpx
from types import SimpleNamespace
import pytest

from openhands.resolver.interfaces.forgejo import ForgejoIssueHandler


def test_get_context_from_external_issues_references_success_round_031(monkeypatch):
    """Covers paths where multiple input sources contribute references, some ids are filtered
    by closing_issue_numbers, and responses may or may not contain a body to append.
    """
    handler = ForgejoIssueHandler('own', 'rep', 'tok', username='me', base_domain='codeberg.org')

    # Controlled extractor: map input strings to deterministic issue id lists
    def fake_extract(text):
        if isinstance(text, str) and 'refer:2' in text:
            return [2]
        if isinstance(text, str) and 'refer:3' in text:
            return [3]
        if isinstance(text, str) and 'refer:4' in text:
            return [4]
        if isinstance(text, str) and 'refer:5' in text:
            return [5]
        return []

    monkeypatch.setattr(
        'openhands.resolver.interfaces.forgejo.extract_issue_references',
        fake_extract,
    )

    calls = []

    class FakeResponse:
        def __init__(self, body_value):
            self._body_value = body_value

        def raise_for_status(self):
            return None

        def json(self):
            # simulate arbitrary JSON payload with optional 'body'
            if self._body_value is None:
                return {}
            return {'body': self._body_value}

    # Build a fake get that returns different bodies depending on the URL (issue id)
    def fake_get(url, headers=None, params=None):
        calls.append((url, headers, params))
        if url.endswith('/3'):
            return FakeResponse('body for 3')
        if url.endswith('/4'):
            # present but empty body -> should not be appended
            return FakeResponse('')
        # default: no body
        return FakeResponse(None)

    monkeypatch.setattr('httpx.get', fake_get)

    closing_issues = []
    # closing_issue_numbers filters out id=2 and id=5, leaving ids 3 and 4 to be fetched
    closing_issue_numbers = [2, 5]
    issue_body = 'refer:2'
    review_comments = ['refer:3']
    review_threads = [SimpleNamespace(comment='refer:4')]
    thread_comments = ['refer:5']

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        issue_body,
        review_comments,
        review_threads,
        thread_comments,
    )

    # result should be the same list object and have only the body for issue 3 appended
    assert result is closing_issues
    assert 'body for 3' in result
    # issue 4 had an empty body and must NOT be appended
    assert all('body for 4' not in v for v in result)

    # Verify we attempted to GET the two unique ids (3 and 4)
    urls = [call[0] for call in calls]
    assert any(url.endswith('/3') for url in urls)
    assert any(url.endswith('/4') for url in urls)


def test_get_context_from_external_issues_references_http_error_round_031(monkeypatch):
    """When fetching an external issue raises httpx.HTTPError, the function should catch it
    and leave the closing_issues list unchanged.
    """
    handler = ForgejoIssueHandler('ownerx', 'repx', 'tokx', username=None, base_domain='codeberg.org')

    # extractor returns a single referenced id
    monkeypatch.setattr(
        'openhands.resolver.interfaces.forgejo.extract_issue_references',
        lambda t: [42],
    )

    class ErrorResponse:
        def raise_for_status(self):
            raise httpx.HTTPError('broken')

        def json(self):
            return {'body': 'should not be used'}

    def fake_get_error(url, headers=None, params=None):
        return ErrorResponse()

    monkeypatch.setattr('httpx.get', fake_get_error)

    closing_issues = []
    closing_issue_numbers = []

    result = handler.get_context_from_external_issues_references(
        closing_issues,
        closing_issue_numbers,
        'something that refers to 42',
        None,
        [],
        None,
    )

    # on HTTP error, nothing appended
    assert result == []
    assert result is closing_issues
