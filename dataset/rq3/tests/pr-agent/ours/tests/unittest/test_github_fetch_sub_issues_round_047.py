import json
import types
from pr_agent.git_providers.github_provider import GithubProvider


class _FakeLogger:
    def __init__(self):
        self.calls = []

    def error(self, *args, **kwargs):
        self.calls.append(("error", args, kwargs))

    def warning(self, *args, **kwargs):
        self.calls.append(("warning", args, kwargs))

    def info(self, *args, **kwargs):
        self.calls.append(("info", args, kwargs))

    def exception(self, *args, **kwargs):
        self.calls.append(("exception", args, kwargs))


class _SequencedRequester:
    def __init__(self, responses):
        # responses: list of values to return on successive requestJson calls
        self._responses = list(responses)
        self.calls = []

    def requestJson(self, method, path, input=None):
        self.calls.append((method, path, input))
        if not self._responses:
            # default to a harmless empty response
            return (200, {}, json.dumps({}))
        return self._responses.pop(0)


def _make_dummy_self_with_responses(responses):
    requester = _SequencedRequester(responses)
    github_client = types.SimpleNamespace()
    # attribute name in code: self.github_client._Github__requester
    # set a mangled-name attribute on the namespace
    setattr(github_client, "_Github__requester", requester)
    dummy_self = types.SimpleNamespace(github_client=github_client)
    return dummy_self, requester


def test_fetch_sub_issues_response_format_error_round_047(monkeypatch):
    """
    If the GraphQL requester returns a non-tuple/non-3-length response for the initial query,
    fetch_sub_issues should log an error and return an empty set.
    """
    fake_logger = _FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: fake_logger
    )

    # First request returns a malformed value (not a 3-tuple)
    dummy_self, requester = _make_dummy_self_with_responses([
        "NOT_A_TUPLE"
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    # Ensure an error was logged mentioning unexpected response format
    assert any(c[0] == "error" and "Unexpected response format" in c[1][0] for c in fake_logger.calls)


def test_fetch_sub_issues_missing_issue_id_round_047(monkeypatch):
    """
    When the first GraphQL response is a proper tuple but lacks an issue id,
    fetch_sub_issues should log a warning and return an empty set.
    """
    fake_logger = _FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: fake_logger
    )

    # Proper 3-tuple, but JSON has repository.issue == None
    first_response = (200, {}, json.dumps({"data": {"repository": {"issue": None}}}))
    dummy_self, requester = _make_dummy_self_with_responses([first_response])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    assert any(c[0] == "warning" and "Issue ID not found" in c[1][0] for c in fake_logger.calls)


def test_fetch_sub_issues_sub_issues_response_format_error_round_047(monkeypatch):
    """
    When the second GraphQL request returns a malformed response (not a 3-tuple),
    the function should log an error with artifact and return an empty set.
    """
    fake_logger = _FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: fake_logger
    )

    # First response contains an issue id
    first_response = (200, {}, json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID"}}}}))
    # Second response is malformed
    second_response = "BAD_SECOND_RESPONSE"

    dummy_self, requester = _make_dummy_self_with_responses([first_response, second_response])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    # The second error call uses the message "Unexpected sub-issues response format"
    assert any(c[0] == "error" and "Unexpected sub-issues response format" in c[1][0] for c in fake_logger.calls)


def test_fetch_sub_issues_invalid_sub_issues_structure_round_047(monkeypatch):
    """
    When the sub-issues JSON does not contain a subIssues key (or it's falsy),
    the function should log an error about invalid structure and return empty set.
    """
    fake_logger = _FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: fake_logger
    )

    first_response = (200, {}, json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID"}}}}))
    # Second response has node but no subIssues (or subIssues falsy)
    second_response = (200, {}, json.dumps({"data": {"node": {}}}))

    dummy_self, requester = _make_dummy_self_with_responses([first_response, second_response])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    assert any(c[0] == "error" and "Invalid sub-issues response structure" in c[1][0] for c in fake_logger.calls)


def test_fetch_sub_issues_nodes_url_extraction_round_047(monkeypatch):
    """
    A valid flow: extract issue id, fetch subIssues node with several nodes where only dicts
    containing 'url' should be added to the returned set. Also exercises the info logging
    with nodes length reported.
    """
    fake_logger = _FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: fake_logger
    )

    first_response = (200, {}, json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID"}}}}))
    nodes = [
        {"url": "https://github.com/owner/repo/issues/2"},
        {"not_url": "ignored"},
        {"url": "https://github.com/owner/repo/issues/3"},
    ]
    second_response_json = {"data": {"node": {"subIssues": {"nodes": nodes}}}}
    second_response = (200, {}, json.dumps(second_response_json))

    dummy_self, requester = _make_dummy_self_with_responses([first_response, second_response])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    # Only entries that contain a 'url' key should be included
    assert result == {"https://github.com/owner/repo/issues/2", "https://github.com/owner/repo/issues/3"}

    # The info log should report the number of nodes fetched (3 in this case)
    assert any(c[0] == "info" and "Github Sub-issues fetched: 3" in c[1][0] for c in fake_logger.calls)
