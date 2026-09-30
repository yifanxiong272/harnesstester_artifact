# file: pr_agent/servers/bitbucket_app.py:86-137
# asked: {"lines": [87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104, 105, 106, 107, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 132, 133, 134, 135, 136, 137], "branches": [[90, 91], [90, 93], [95, 96], [95, 97], [97, 98], [97, 99], [105, 106], [105, 109], [112, 114], [112, 117], [118, 119], [118, 122], [129, 130], [129, 132]]}
# gained: {"lines": [87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104, 105, 106, 107, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 132, 133, 134, 135, 136, 137], "branches": [[90, 91], [90, 93], [95, 96], [95, 97], [97, 98], [97, 99], [105, 106], [105, 109], [112, 114], [112, 117], [118, 119], [118, 122], [129, 130], [129, 132]]}

import pytest
import types
from datetime import datetime, timedelta

import pr_agent.servers.bitbucket_app as bb


class DummyLogger:
    def __init__(self):
        self.records = []

    def error(self, msg, **kwargs):
        self.records.append(('error', msg, kwargs))

    def warning(self, msg, **kwargs):
        self.records.append(('warning', msg, kwargs))

    def debug(self, msg, **kwargs):
        self.records.append(('debug', msg, kwargs))

    def exception(self, msg, **kwargs):
        self.records.append(('exception', msg, kwargs))


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_no_data_returns_true_and_logs_error(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    # context shouldn't be touched here but ensure it's present
    monkeypatch.setattr(bb.context, "get", lambda key: None)

    result = await bb._validate_time_from_last_commit_to_pr_update({})
    assert result is True
    assert any(r[0] == 'error' and "No data found" in r[1] for r in logger.records)


@pytest.mark.asyncio
async def test_missing_commits_api_returns_false(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")
    data = {"data": {"pullrequest": {"links": {}}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False


@pytest.mark.asyncio
async def test_missing_updated_on_returns_false(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")
    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}}}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False


@pytest.mark.asyncio
async def test_requests_status_non_200_returns_false_and_logs_warning(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    # Response with non-200 status
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(status_code=500))

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": "2023-01-01T00:00:00"}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False
    assert any(r[0] == 'warning' and "Bitbucket commits API returned 500" in r[1] for r in logger.records)


@pytest.mark.asyncio
async def test_missing_commit_fields_returns_false_and_logs_warning(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    # Response with 200 but values missing required nested fields
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(200, {"values": []}))
    monkeypatch.setattr(bb, "_get_username", lambda data: "Some User")

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": "2023-01-01T00:00:00"}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False
    assert any(r[0] == 'warning' and "No commits returned for pull request" in r[1] for r in logger.records)


@pytest.mark.asyncio
async def test_username_mismatch_returns_false_and_logs_warning(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    commits = {
        "values": [
            {"author": {"user": {"display_name": "Commit User"}}, "date": "2023-01-01T00:00:00"}
        ]
    }
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(200, commits))
    # _get_username returns a different user
    monkeypatch.setattr(bb, "_get_username", lambda data: "Different User")

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": "2023-01-01T00:00:01"}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False
    assert any(r[0] == 'warning' and "Mismatch in username" in r[1] for r in logger.records)


@pytest.mark.asyncio
async def test_valid_time_window_returns_true(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    # Make commit date 10 seconds before PR updated -> within 15s window
    updated = datetime.now().replace(microsecond=0)
    commit = updated - timedelta(seconds=10)
    commits = {
        "values": [
            {"author": {"user": {"display_name": "Matching User"}}, "date": commit.isoformat()}
        ]
    }
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(200, commits))
    monkeypatch.setattr(bb, "_get_username", lambda data: "Matching User")

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": updated.isoformat()}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is True


@pytest.mark.asyncio
async def test_time_diff_too_large_logs_debug_and_returns_false(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    # Make commit date 60 seconds before PR updated -> too large
    updated = datetime.now().replace(microsecond=0)
    commit = updated - timedelta(seconds=60)
    commits = {
        "values": [
            {"author": {"user": {"display_name": "Matching User"}}, "date": commit.isoformat()}
        ]
    }
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(200, commits))
    monkeypatch.setattr(bb, "_get_username", lambda data: "Matching User")

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": updated.isoformat()}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False
    assert any(r[0] == 'debug' and "Too much time passed since last commit" in r[1] for r in logger.records)


@pytest.mark.asyncio
async def test_exception_in_username_logs_exception_and_returns_false(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb, "get_logger", lambda: logger)
    monkeypatch.setattr(bb.context, "get", lambda key: "token")

    # Provide valid response so the code reaches the _get_username call and then raise
    commits = {
        "values": [
            {"author": {"user": {"display_name": "ShouldNotMatter"}}, "date": "2023-01-01T00:00:00"}
        ]
    }
    monkeypatch.setattr(bb.requests, "get", lambda url, headers: DummyResponse(200, commits))

    def raise_error(data):
        raise RuntimeError("boom")

    monkeypatch.setattr(bb, "_get_username", raise_error)

    data = {"data": {"pullrequest": {"links": {"commits": {"href": "http://example.com/commits"}},
                                       "updated_on": "2023-01-01T00:00:01"}}}

    result = await bb._validate_time_from_last_commit_to_pr_update(data)
    assert result is False
    assert any(r[0] == 'exception' and "Failed to validate time difference" in r[1] for r in logger.records)
