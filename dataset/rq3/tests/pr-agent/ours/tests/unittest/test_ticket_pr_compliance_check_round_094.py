import pytest

from pr_agent.tools import ticket_pr_compliance_check as tpc


class FakePattern:
    def __init__(self, matches=None, raise_exc=False):
        self._matches = matches or []
        self._raise = raise_exc

    def findall(self, text):
        if self._raise:
            raise ValueError("boom")
        return self._matches


class FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def info(self, msg):
        self.info_calls.append(msg)

    def error(self, msg, artifact=None):
        # preserve shape used by callers
        self.error_calls.append({"msg": msg, "artifact": artifact})


def test_mixed_matches_and_limit_round_094(monkeypatch):
    """
    Cover full-URL, shorthand (owner/repo#), and #123 style matches plus the
    branch that limits to 3 tickets and logs an info message.
    """
    # Prepare a variety of matches. Each tuple emulates the groups the
    # original regex/findall is expected to return (indices 0..5 used).
    full_url = ("https://github.com/own/repo/issues/1", "", "", "", "", "")
    shorthand = ("", "owner/repo#2", "owner", "repo", "2", "")
    hash_short = ("", "", "", "", "", "#3")
    extra_full_1 = ("https://github.com/x/y/issues/4", "", "", "", "", "")
    extra_full_2 = ("https://github.com/a/b/issues/5", "", "", "", "", "")

    matches = [full_url, shorthand, hash_short, extra_full_1, extra_full_2]

    fake_pattern = FakePattern(matches=matches)
    fake_logger = FakeLogger()

    monkeypatch.setattr(tpc, "GITHUB_TICKET_PATTERN", fake_pattern)
    # patch get_logger to return our fake logger instance
    monkeypatch.setattr(tpc, "get_logger", lambda: fake_logger)

    # repo_path provided so #3 can be resolved into a full URL
    result = tpc.extract_ticket_links_from_pr_description("irrelevant text", "my/repo", base_url_html="https://github.com/")

    # We expect the function to limit the results to 3 entries when more than 3 unique tickets
    assert isinstance(result, list)
    assert len(result) == 3

    # Validate that each returned URL is one of the constructed/observed URLs
    expected_urls = {
        "https://github.com/own/repo/issues/1",
        "https://github.com/owner/repo/issues/2",
        "https://github.com/my/repo/issues/3",
        "https://github.com/x/y/issues/4",
        "https://github.com/a/b/issues/5",
    }
    for url in result:
        assert url in expected_urls

    # Because there were more than 3 tickets, an info log should have been emitted
    assert any("Too many tickets" in msg for msg in fake_logger.info_calls)


def test_hash_skipped_when_invalid_or_no_repo_round_094(monkeypatch):
    """
    Ensure that #abc (non-digit) and missing repo_path do not produce a ticket URL.
    """
    matches = [("", "", "", "", "", "#abc")]
    fake_pattern = FakePattern(matches=matches)
    fake_logger = FakeLogger()

    monkeypatch.setattr(tpc, "GITHUB_TICKET_PATTERN", fake_pattern)
    monkeypatch.setattr(tpc, "get_logger", lambda: fake_logger)

    # Provide no repo_path -> should not add any ticket URL for a #... match
    result_none_repo = tpc.extract_ticket_links_from_pr_description("irrelevant", None, base_url_html="https://github.com")
    assert result_none_repo == []

    # Provide repo_path but non-digit issue number -> still should not add
    result_invalid_number = tpc.extract_ticket_links_from_pr_description("irrelevant", "org/repo", base_url_html="https://github.com")
    assert result_invalid_number == []


def test_exception_handling_round_094(monkeypatch):
    """
    Force the pattern's findall to raise and verify the exception branch logs an error and
    that the function returns an empty list (graceful failure).
    """
    fake_pattern = FakePattern(raise_exc=True)
    fake_logger = FakeLogger()

    monkeypatch.setattr(tpc, "GITHUB_TICKET_PATTERN", fake_pattern)
    monkeypatch.setattr(tpc, "get_logger", lambda: fake_logger)

    result = tpc.extract_ticket_links_from_pr_description("any", "repo/path", base_url_html="https://github.com")

    assert result == []
    # Ensure error log was called with the expected message fragment and artifact shape
    assert any("Error extracting tickets error=" in e["msg"] for e in fake_logger.error_calls)
    # artifact should be present and include a traceback key in the logged shape
    artefacts = [e["artifact"] for e in fake_logger.error_calls if e.get("artifact") is not None]
    # The code passes a dict with a 'traceback' key; ensure shape matches
    assert any(isinstance(a, dict) and "traceback" in a for a in artefacts)
