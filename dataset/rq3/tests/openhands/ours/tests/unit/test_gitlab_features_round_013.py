import pytest
from types import SimpleNamespace, MethodType

from openhands.integrations.gitlab.service.features import GitLabFeaturesMixin
from openhands.integrations.service_types import (
    ProviderType,
    RequestMethod,
    SuggestedTask,
    TaskType,
)


def build_bound_instance(graphql_response=None, issues_response=None, username="alice"):
    """Create a minimal object with the attributes and async helpers
    that GitLabFeaturesMixin.get_suggested_tasks expects.

    - graphql_response: dict returned by execute_graphql_query
    - issues_response: list returned by _make_request (first element)
    """

    obj = SimpleNamespace()

    async def get_user():
        # get_suggested_tasks expects user.login
        return SimpleNamespace(login=username)

    async def execute_graphql_query(query):
        if isinstance(graphql_response, Exception):
            # allow tests to simulate exceptions
            raise graphql_response
        return graphql_response or {}

    async def _make_request(method, url, params):
        # method param will be RequestMethod.GET in production code
        return (issues_response or [], None)

    obj.get_user = get_user
    obj.execute_graphql_query = execute_graphql_query
    obj._make_request = _make_request
    obj.BASE_URL = "https://gitlab.example/api"

    # Bind the mixin's coroutine method to our lightweight object
    obj.get_suggested_tasks = MethodType(GitLabFeaturesMixin.get_suggested_tasks, obj)

    return obj


@pytest.mark.asyncio
async def test_merge_request_branches_round_013():
    # Construct GraphQL response with multiple MRs to exercise branches:
    # - conflicts -> MERGE_CONFLICTS
    # - pipeline FAILED -> FAILING_CHECKS
    # - unresolved comments -> UNRESOLVED_COMMENTS
    # - a plain open MR should not be included (OPEN_PR filtered out)
    graphql_response = {
        "currentUser": {
            "authoredMergeRequests": {
                "nodes": [
                    {
                        "project": {"fullPath": "org/repo_conflicts"},
                        "iid": 1,
                        "title": "conflict",
                        "conflicts": True,
                    },
                    {
                        "project": {"fullPath": "org/repo_failed"},
                        "iid": 2,
                        "title": "failed",
                        "conflicts": False,
                        "pipelines": {"nodes": [{"status": "FAILED"}]},
                    },
                    {
                        "project": {"fullPath": "org/repo_unresolved"},
                        "iid": 3,
                        "title": "unresolved",
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
                    },
                    {
                        "project": {"fullPath": "org/repo_open"},
                        "iid": 4,
                        "title": "open",
                        "conflicts": False,
                        "pipelines": {"nodes": []},
                        "discussions": {"nodes": []},
                    },
                ]
            }
        }
    }

    instance = build_bound_instance(graphql_response=graphql_response, issues_response=[])

    tasks = await instance.get_suggested_tasks()

    # We expect three tasks (conflicts, failing checks, unresolved comments)
    assert isinstance(tasks, list)
    assert len(tasks) == 3

    types_seen = {t.task_type for t in tasks}
    assert TaskType.MERGE_CONFLICTS in types_seen
    assert TaskType.FAILING_CHECKS in types_seen
    assert TaskType.UNRESOLVED_COMMENTS in types_seen

    # Validate repo names and issue identifiers were passed through
    by_type = {t.task_type: t for t in tasks}
    assert by_type[TaskType.MERGE_CONFLICTS].repo == "org/repo_conflicts"
    assert by_type[TaskType.MERGE_CONFLICTS].issue_number == 1
    assert by_type[TaskType.FAILING_CHECKS].repo == "org/repo_failed"
    assert by_type[TaskType.FAILING_CHECKS].issue_number == 2
    assert by_type[TaskType.UNRESOLVED_COMMENTS].repo == "org/repo_unresolved"
    assert by_type[TaskType.UNRESOLVED_COMMENTS].issue_number == 3


@pytest.mark.asyncio
async def test_issues_and_repo_parsing_round_013():
    # GraphQL returns no authored MRs
    graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": []}}}

    # REST issues returned by _make_request: ensure references.full -> repo name extraction
    issues_response = [
        {
            "references": {"full": "group/repo#42"},
            "iid": 42,
            "title": "Important bug",
        },
        {
            # include whitespace to ensure .strip() is exercised
            "references": {"full": "  group/other_repo#7  "},
            "iid": 7,
            "title": "Another issue",
        },
    ]

    instance = build_bound_instance(graphql_response=graphql_response, issues_response=issues_response)

    tasks = await instance.get_suggested_tasks()

    # Both issues should produce OPEN_ISSUE tasks
    assert len(tasks) == 2
    for t in tasks:
        assert t.git_provider == ProviderType.GITLAB
        assert t.task_type == TaskType.OPEN_ISSUE
        assert isinstance(t.repo, str) and t.repo != ""
        assert isinstance(t.issue_number, int)
        assert isinstance(t.title, str)

    # Check correct parsing of repo names and issue numbers
    repo_by_number = {t.issue_number: t.repo for t in tasks}
    assert repo_by_number[42] == "group/repo"
    assert repo_by_number[7] == "group/other_repo"


@pytest.mark.asyncio
async def test_exception_returns_empty_round_013():
    # Simulate execute_graphql_query raising an exception to hit the except: return [] branch
    instance = build_bound_instance(graphql_response=Exception("boom"), issues_response=[{}])

    result = await instance.get_suggested_tasks()

    assert result == []
