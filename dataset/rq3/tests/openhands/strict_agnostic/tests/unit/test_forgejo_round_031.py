import httpx
import pytest

from openhands.resolver.interfaces.forgejo import ForgejoIssueHandler


class SimpleThread:
    def __init__(self, comment: str):
        self.comment = comment


def _digit_extractor(s: str) -> list[int]:
    """
    Deterministic extractor for tests: returns all integers found in the input string.
    This will be monkeypatched over the module-level extract_issue_references.
    """
    if not s:
        return []
    nums = []
    cur = ''
    for ch in s:
        if ch.isdigit():
            cur += ch
        else:
            if cur:
                nums.append(int(cur))
                cur = ''
    if cur:
        nums.append(int(cur))
    return nums


def test_get_context_success_round_031(monkeypatch):
    """
    - Patch extract_issue_references to extract digits deterministically.
    - Patch httpx.get to return a FakeResponse: some ids return a body, one id raises HTTPError.
    - Verify bodies for successful fetch are appended to closing_issues and errors are swallowed.
    """

    # Monkeypatch the module-level extractor used by the target function
    monkeypatch.setattr(
        'openhands.resolver.interfaces.forgejo.extract_issue_references',
        _digit_extractor,
    )

    # Build a fake httpx.get that responds differently depending on the final path segment
    class FakeResponse:
        def __init__(self, issue_id: int, raise_error: bool = False, body: str = ''):
            self._id = issue_id
            self._raise = raise_error
            self._body = body

        def raise_for_status(self):
            if self._raise:
                # Use httpx.HTTPError to match the caught exception type in the implementation
                raise httpx.HTTPError(f'status error for {self._id}')

        def json(self):
            return {'body': self._body}

    def fake_get(url, headers=None):
        # Expect url ends with /<issue_number>
        try:
            issue_number = int(url.rstrip('/').split('/')[-1])
        except Exception:
            # Simulate a safe default behavior
            return FakeResponse(-1, raise_error=True)

        # For deterministic branching in this test:
        # - id 2 -> success with body
        # - id 3 -> error on raise_for_status
        # - id 4 -> success but empty body
        if issue_number == 2:
            return FakeResponse(2, raise_error=False, body='body_for_2')
        if issue_number == 3:
            return FakeResponse(3, raise_error=True, body='body_for_3')
        if issue_number == 4:
            return FakeResponse(4, raise_error=False, body='')
        return FakeResponse(issue_number, raise_error=False, body=f'body_for_{issue_number}')

    monkeypatch.setattr(httpx, 'get', fake_get)

    # Create handler and override download url to a controlled prefix
    handler = ForgejoIssueHandler('owner', 'repo', 'token', 'username', 'example.com')
    # Ensure the download_url used in implementation is deterministic
    monkeypatch.setattr(handler, 'get_download_url', lambda: 'http://fake/issue')
    # Ensure headers attribute exists and is used (value irrelevant for test)
    handler.headers = {'Authorization': 'token'}

    # Prepare inputs that will produce references: issue_body, review_comments, review_threads, thread_comments
    closing_issues = ['existing_issue_text']
    closing_issue_numbers = [1]

    # The extractor returns [2] for issue_body, [3] for review_comments entry, [2] for a review thread comment,
    # and [4] for a thread comment. Unique ids -> {2,3,4}
    issue_body = 'refs 2'
    review_comments = ['refs 3']
    review_threads = [SimpleThread('refs 2')]
    thread_comments = ['refs 4']

    result = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues,
        closing_issue_numbers=closing_issue_numbers,
        issue_body=issue_body,
        review_comments=review_comments,
        review_threads=review_threads,
        thread_comments=thread_comments,
    )

    # Assertions (observable behavior):
    # - The original closing issue text remains.
    # - body_for_2 was appended because id 2 returned a body and is not in closing_issue_numbers.
    # - id 3 raised an HTTPError and therefore its body is not appended.
    # - id 4 returned empty body so nothing appended for it.
    assert 'existing_issue_text' in result
    assert 'body_for_2' in result
    assert not any('body_for_3' in r for r in result)
    # no body added for 4 since its body was empty
    assert not any('body_for_4' in r for r in result)


def test_get_context_filters_and_dedup_round_031(monkeypatch):
    """
    - Ensure that references that are already in closing_issue_numbers are filtered out.
    - Ensure duplicate references lead to a single request (dedup via set) by counting calls.
    """

    monkeypatch.setattr(
        'openhands.resolver.interfaces.forgejo.extract_issue_references',
        _digit_extractor,
    )

    call_counter = {'count': 0}

    class FakeResponse2:
        def __init__(self, issue_id: int, body: str = ''):
            self._id = issue_id
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return {'body': self._body}

    def fake_get_counting(url, headers=None):
        call_counter['count'] += 1
        try:
            issue_number = int(url.rstrip('/').split('/')[-1])
        except Exception:
            issue_number = -1
        return FakeResponse2(issue_number, body=f'body_for_{issue_number}')

    monkeypatch.setattr(httpx, 'get', fake_get_counting)

    handler = ForgejoIssueHandler('owner', 'repo', 'token', 'username', 'example.com')
    monkeypatch.setattr(handler, 'get_download_url', lambda: 'http://fake/issue')
    handler.headers = {'Authorization': 'token'}

    # closing_issue_numbers already includes 2 and 3; references include 2, 3, and 5 twice -> only 5 should be queried
    closing_issues = []
    closing_issue_numbers = [2, 3]

    issue_body = ''  # falsy branch for issue_body
    review_comments = None  # falsy branch
    review_threads = [SimpleThread('refs 5'), SimpleThread('refs 5')]
    thread_comments = None

    result = handler.get_context_from_external_issues_references(
        closing_issues=closing_issues,
        closing_issue_numbers=closing_issue_numbers,
        issue_body=issue_body,
        review_comments=review_comments,
        review_threads=review_threads,
        thread_comments=thread_comments,
    )

    # Only one unique id (5) should have been fetched despite appearing twice
    assert call_counter['count'] == 1
    assert any('body_for_5' in r for r in result)
