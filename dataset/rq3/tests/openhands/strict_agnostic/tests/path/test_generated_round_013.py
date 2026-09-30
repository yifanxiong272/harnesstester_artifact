import types
import asyncio
from typing import Any

from openhands.integrations.gitlab.service import features
from openhands.integrations.service_types import (
    ProviderType,
    RequestMethod,
    SuggestedTask,
    TaskType,
)


class _DummySelf:
    """Lightweight dummy that provides the async interface used by
    GitLabFeaturesMixin.get_suggested_tasks. We keep it minimal and
    deterministic: no network, no external calls.
    """

    def __init__(
        self,
        user_login: str = "alice",
        graphql_response: dict | None = None,
        issues_response: list[dict] | None = None,
        raise_graphql: bool = False,
        raise_request: bool = False,
    ) -> None:
        self.BASE_URL = "https://gitlab.example"
        self._user_login = user_login
        self._graphql_response = graphql_response or {}
        self._issues_response = issues_response or []
        self._raise_graphql = raise_graphql
        self._raise_request = raise_request

        # record last request for inspection
        self.last_request: dict[str, Any] = {}

    async def get_user(self):
        # returns a simple object with .login attribute
        return types.SimpleNamespace(login=self._user_login)

    async def execute_graphql_query(self, query: str) -> dict:
        if self._raise_graphql:
            raise Exception("graphql-failed")
        # return a shallow copy to avoid accidental test mutation
        return dict(self._graphql_response)

    async def _make_request(self, method: RequestMethod, url: str, params: dict):
        self.last_request = {"method": method, "url": url, "params": dict(params)}
        if self._raise_request:
            raise Exception("request-failed")
        # mimic original: returns (issues_response, _)
        return (list(self._issues_response), None)


# Helpers to run the async method synchronously in pytest tests
def _run_get_suggested(dummy: _DummySelf):
    return asyncio.get_event_loop().run_until_complete(
        features.GitLabFeaturesMixin.get_suggested_tasks(dummy)
    )


def test_merge_conflicts_round_013():
    # MR with conflicts should map to TaskType.MERGE_CONFLICTS
    mr = {
        "iid": 42,
        "title": "Conflict MR",
        "project": {"fullPath": "group/repo"},
        "conflicts": True,
        # other fields present but irrelevant
        "pipelines": {"nodes": []},
        "discussions": {"nodes": []},
    }
    graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    dummy = _DummySelf(graphql_response=graphql_response, issues_response=[])

    tasks = _run_get_suggested(dummy)

    assert isinstance(tasks, list)
    assert len(tasks) == 1
    t = tasks[0]
    assert isinstance(t, SuggestedTask)
    assert t.git_provider == ProviderType.GITLAB
    assert t.task_type == TaskType.MERGE_CONFLICTS
    assert t.repo == "group/repo"
    assert t.issue_number == 42
    assert t.title == "Conflict MR"


def test_failed_pipeline_round_013():
    # MR whose pipeline status is FAILED should map to FAILING_CHECKS
    mr = {
        "iid": 101,
        "title": "Bad pipeline",
        "project": {"fullPath": "group/ci-repo"},
        "conflicts": False,
        "pipelines": {"nodes": [{"status": "FAILED"}]},
        "discussions": {"nodes": []},
    }
    graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    dummy = _DummySelf(graphql_response=graphql_response, issues_response=[])

    tasks = _run_get_suggested(dummy)

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.FAILING_CHECKS
    assert t.repo == "group/ci-repo"
    assert t.issue_number == 101
    assert t.title == "Bad pipeline"


def test_unresolved_comments_round_013():
    # MR with an unresolved, resolvable note should map to UNRESOLVED_COMMENTS
    mr = {
        "iid": 7,
        "title": "Please review",
        "project": {"fullPath": "example/with-comments"},
        "conflicts": False,
        "pipelines": {"nodes": []},
        "discussions": {
            "nodes": [
                {
                    "notes": {
                        "nodes": [
                            {"resolvable": True, "resolved": False}
                        ]
                    }
                }
            ]
        },
    }
    graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    dummy = _DummySelf(graphql_response=graphql_response, issues_response=[])

    tasks = _run_get_suggested(dummy)

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.UNRESOLVED_COMMENTS
    assert t.repo == "example/with-comments"
    assert t.issue_number == 7
    assert t.title == "Please review"


def test_issues_processing_round_013():
    # Issues returned from the REST request should be converted to OPEN_ISSUE
    issue = {
        "iid": 9,
        "title": "Bug found",
        "references": {"full": "somegroup/somerepo#9"},
    }
    graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": []}}}
    dummy = _DummySelf(graphql_response=graphql_response, issues_response=[issue], user_login="bob")

    tasks = _run_get_suggested(dummy)

    # One issue task added
    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.OPEN_ISSUE
    # repo should be the part before the '#'
    assert t.repo == "somegroup/somerepo"
    assert t.issue_number == 9
    assert t.title == "Bug found"

    # ensure the request was directed to BASE_URL + '/issues' and contained the assignee username
    assert dummy.last_request["url"] == f"{dummy.BASE_URL}/issues"
    assert dummy.last_request["params"]["assignee_username"] == "bob"
    assert dummy.last_request["params"]["state"] == "opened"


def test_exception_returns_empty_round_013():
    # If the GraphQL call raises, get_suggested_tasks should swallow and return []
    dummy = _DummySelf(raise_graphql=True, graphql_response={})

    tasks = _run_get_suggested(dummy)

    assert tasks == []
