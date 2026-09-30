import json
from types import SimpleNamespace
import pytest

from pr_agent.git_providers.github_provider import GithubProvider


class DummyRequester:
    """A deterministic requester that returns preset responses in order and records calls."""

    def __init__(self, responses):
        # responses is a list; each element will be returned in sequence
        self.responses = list(responses)
        self.calls = []

    def requestJson(self, method, path, input=None):
        # record call signature for assertions
        self.calls.append((method, path, input))
        if not self.responses:
            return None
        return self.responses.pop(0)


def make_dummy_self_with_responses(responses):
    requester = DummyRequester(responses)
    github_client = SimpleNamespace(_Github__requester=requester)
    return SimpleNamespace(github_client=github_client), requester


def test_unexpected_first_response_round_047():
    """If the first requestJson returns a non-tuple, the function should return an empty set."""
    dummy_self, requester = make_dummy_self_with_responses([
        {"not": "a tuple"},
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    # Should return empty set when the top-level response format is unexpected
    assert result == set()
    # Ensure we attempted the GraphQL POST to the expected path
    assert requester.calls[0][0] == "POST"
    assert requester.calls[0][1] == "/graphql"


def test_missing_issue_id_round_047():
    """If the GraphQL response is a tuple but lacks an issue id, returns empty set."""
    first_response_json = json.dumps({"data": {"repository": {"issue": None}}})
    dummy_self, requester = make_dummy_self_with_responses([
        (200, {}, first_response_json),
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    # Only the first request (to fetch issue id) should have been made
    assert len(requester.calls) == 1


def test_unexpected_second_response_round_047():
    """If the second request (sub-issues) returns a non-tuple, returns empty set after first succeeded."""
    first_response_json = json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID_1"}}}})
    # second response will be None (non-tuple), simulating an unexpected format
    dummy_self, requester = make_dummy_self_with_responses([
        (200, {}, first_response_json),
        None,
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()
    # We should have called the requester twice: one for issue id, one for sub-issues
    assert len(requester.calls) >= 2
    assert requester.calls[0][1] == "/graphql"
    assert requester.calls[1][1] == "/graphql"


def test_invalid_subissues_structure_round_047():
    """If the sub-issues response lacks the expected subIssues structure, return empty set."""
    first_response_json = json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID_2"}}}})
    # second response is tuple but node/subIssues absent
    second_response_json = json.dumps({"data": {"node": None}})
    dummy_self, requester = make_dummy_self_with_responses([
        (200, {}, first_response_json),
        (200, {}, second_response_json),
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    assert result == set()


def test_happy_path_collects_urls_round_047():
    """When responses are well-formed, collect only nodes that include 'url' key."""
    first_response_json = json.dumps({"data": {"repository": {"issue": {"id": "ISSUE_ID_3"}}}})
    nodes = [
        {"url": "https://github.com/owner/repo/issues/2"},
        {"something_else": "no url here"},
        {"url": "https://github.com/owner/repo/issues/3"},
    ]
    second_response_json = json.dumps({"data": {"node": {"subIssues": {"nodes": nodes}}}})

    dummy_self, requester = make_dummy_self_with_responses([
        (200, {}, first_response_json),
        (200, {}, second_response_json),
    ])

    result = GithubProvider.fetch_sub_issues(dummy_self, "https://github.com/owner/repo/issues/1")

    # Only the two URLs should be collected; ordering is not important as result is a set
    assert result == {
        "https://github.com/owner/repo/issues/2",
        "https://github.com/owner/repo/issues/3",
    }
    # verify both GraphQL calls were made
    assert len(requester.calls) == 2
    assert all(call[0] == "POST" and call[1] == "/graphql" for call in requester.calls)
