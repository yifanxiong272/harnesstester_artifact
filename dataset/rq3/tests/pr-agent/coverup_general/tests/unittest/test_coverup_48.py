# file: pr_agent/tools/ticket_pr_compliance_check.py:38-66
# asked: {"lines": [42, 43, 45, 47, 48, 49, 50, 51, 52, 54, 55, 56, 58, 59, 61, 62, 63, 64, 66], "branches": [[47, 48], [47, 58], [48, 49], [48, 50], [50, 51], [50, 54], [55, 47], [55, 56], [58, 59], [58, 66]]}
# gained: {"lines": [42, 43, 45, 47, 48, 49, 50, 51, 52, 54, 55, 56, 58, 59, 61, 62, 63, 64, 66], "branches": [[47, 48], [47, 58], [48, 49], [48, 50], [50, 51], [50, 54], [55, 56], [58, 59]]}

import traceback
import types
import pytest

import pr_agent.tools.ticket_pr_compliance_check as tpc


class FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))


class PatternReturning:
    def __init__(self, matches):
        # matches should be a list of tuples; findall returns that list
        self._matches = matches

    def findall(self, text):
        return list(self._matches)


class PatternRaising:
    def __init__(self, exc):
        self._exc = exc

    def findall(self, text):
        raise self._exc


def make_match_full_url(url):
    # match[0] truthy -> full URL
    # create at least 6 elements to match indexing in function
    return (url, '', '', '', '', '')


def make_match_shorthand(owner, repo, issue):
    # match[0] falsey, match[1] truthy, match[2]=owner, [3]=repo, [4]=issue
    return ('', '#shorthand', owner, repo, issue, '')


def make_match_hash(issue):
    # match[0] and match[1] falsey, match[5] holds '#123'
    return ('', '', '', '', '', f'#{issue}')


def test_extract_ticket_links_various_and_truncation(monkeypatch):
    fake_logger = FakeLogger()
    # prepare matches: one full url, one shorthand, three hash issues -> total 5 unique tickets
    matches = [
        make_match_full_url('https://github.com/ownerX/repoX/issues/100'),
        make_match_shorthand('ownerY', 'repoY', '200'),
        make_match_hash('1'),
        make_match_hash('2'),
        make_match_hash('3')
    ]
    # monkeypatch pattern and logger in module
    monkeypatch.setattr(tpc, 'GITHUB_TICKET_PATTERN', PatternReturning(matches))
    monkeypatch.setattr(tpc, 'get_logger', lambda: fake_logger)

    # use a repo_path so hash (#) issues are converted
    result = tpc.extract_ticket_links_from_pr_description("unused text", repo_path='my/repo')

    # Should truncate to 3 items due to >3 tickets
    assert isinstance(result, list)
    assert len(result) == 3

    # All returned items should look like issue URLs on github (start with https://github.com)
    for item in result:
        assert item.startswith('https://github.com/')

    # Ensure that info was logged about too many tickets and mentions a count > 3 (5 expected)
    assert fake_logger.info_calls, "Expected logger.info to be called for too many tickets"
    # Look for the message content
    info_args, info_kwargs = fake_logger.info_calls[0]
    # first positional arg is the message
    assert any("Too many tickets found in PR description" in str(arg) for arg in info_args)

    # Also ensure that at least one of the known generated URLs is present in the original set
    # (we can't rely on ordering due to set -> list conversion)
    possible_urls = {
        'https://github.com/ownerX/repoX/issues/100',
        'https://github.com/ownerY/repoY/issues/200',
        'https://github.com/my/repo/issues/1',
        'https://github.com/my/repo/issues/2',
        'https://github.com/my/repo/issues/3',
    }
    assert set(result).issubset(possible_urls)
    # cleanup is done by monkeypatch fixture


def test_extract_ticket_links_handles_exception_and_logs(monkeypatch):
    fake_logger = FakeLogger()
    # pattern that raises an exception when findall is called
    monkeypatch.setattr(tpc, 'GITHUB_TICKET_PATTERN', PatternRaising(ValueError("boom")))
    monkeypatch.setattr(tpc, 'get_logger', lambda: fake_logger)

    res = tpc.extract_ticket_links_from_pr_description("anything", repo_path='any/repo')

    # On exception, function should return empty list
    assert res == []

    # Ensure logger.error was called and that artifact contains a traceback string
    assert fake_logger.error_calls, "Expected logger.error to be called on exception"
    (err_args, err_kwargs) = fake_logger.error_calls[0]
    # first positional arg is the message
    assert any("Error extracting tickets" in str(arg) for arg in err_args)
    # artifact kw should be present and contain 'traceback'
    assert 'artifact' in err_kwargs
    artifact = err_kwargs['artifact']
    assert isinstance(artifact, dict)
    assert 'traceback' in artifact
    assert 'ValueError' in artifact['traceback'] or 'boom' in artifact['traceback']
