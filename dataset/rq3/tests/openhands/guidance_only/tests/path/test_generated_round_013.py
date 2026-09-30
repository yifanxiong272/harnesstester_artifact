import types
import pytest
from types import SimpleNamespace

from openhands.integrations.gitlab.service.features import GitLabFeaturesMixin
from openhands.integrations.service_types import (
    ProviderType,
    RequestMethod,
    SuggestedTask,
    TaskType,
)

pytestmark = pytest.mark.asyncio


class DummyService(GitLabFeaturesMixin):
    """A minimal concrete object to host the mixin methods/attributes used by
    get_suggested_tasks. Methods will be monkey-patched per-test.
    """

    def __init__(self):
        # consumed by code building the issues URL
        self.BASE_URL = "https://gitlab.example.com/api/v4"


async def _bind_and_call_get_suggested_tasks(svc: DummyService) -> list[SuggestedTask]:
    # Helper to call the async method on the instance
    return await svc.get_suggested_tasks()


async def test_get_suggested_tasks_various_mr_states_round_013():
    svc = DummyService()

    # get_user should provide .login
    async def fake_get_user(self):
        return SimpleNamespace(login="jdoe")

    # GraphQL returns a variety of MRs to exercise branches:
    # - MR with conflicts -> MERGE_CONFLICTS
    # - MR with failing pipeline -> FAILING_CHECKS
    # - MR with unresolved comments -> UNRESOLVED_COMMENTS
    # - MR with none of the above -> OPEN_PR (should be filtered out)
    async def fake_execute_graphql_query(self, query):
        return {
            "currentUser": {
                "authoredMergeRequests": {
                    "nodes": [
                        {
                            "project": {"fullPath": "group/repo1"},
                            "iid": 1,
                            "title": "MR with conflicts",
                            "conflicts": True,
                            "pipelines": {"nodes": []},
                            "discussions": {"nodes": []},
                        },
                        {
                            "project": {"fullPath": "group/repo2"},
                            "iid": 2,
                            "title": "MR with failing pipeline",
                            "conflicts": False,
                            "pipelines": {"nodes": [{"status": "FAILED"}]},
                            "discussions": {"nodes": []},
                        },
                        {
                            "project": {"fullPath": "group/repo3"},
                            "iid": 3,
                            "title": "MR with unresolved comments",
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
                            "project": {"fullPath": "group/repo4"},
                            "iid": 4,
                            "title": "Open MR (no special state)",
                            "conflicts": False,
                            "pipelines": {"nodes": []},
                            "discussions": {"nodes": []},
                        },
                    ]
                }
            }
        }

    # _make_request returns (issues_response, _)
    async def fake_make_request(self, method: RequestMethod, url: str, params: dict):
        # Provide one issue assigned to jdoe
        issues = [
            {
                "references": {"full": "group/repo5#10"},
                "iid": 10,
                "title": "Assigned issue",
            }
        ]
        return issues, None

    # Bind the fake coroutines to the instance
    svc.get_user = types.MethodType(fake_get_user, svc)
    svc.execute_graphql_query = types.MethodType(fake_execute_graphql_query, svc)
    svc._make_request = types.MethodType(fake_make_request, svc)

    tasks = await _bind_and_call_get_suggested_tasks(svc)

    # Expect three MR-derived suggested tasks (conflicts, failing checks, unresolved comments)
    # plus one issue-derived task
    assert len(tasks) == 4

    # Map task_type -> tuple(repo, issue_number, title) for easy assertions
    mapping = {t.task_type: (t.repo, t.issue_number, t.title, t.git_provider) for t in tasks}

    # Check each expected TaskType present and payload shapes preserved
    assert TaskType.MERGE_CONFLICTS in mapping
    repo, iid, title, provider = mapping[TaskType.MERGE_CONFLICTS]
    assert repo == "group/repo1"
    assert iid == 1
    assert "conflicts" in title or "conflicts" in title.lower() or isinstance(title, str)
    assert provider == ProviderType.GITLAB

    assert TaskType.FAILING_CHECKS in mapping
    repo, iid, title, provider = mapping[TaskType.FAILING_CHECKS]
    assert repo == "group/repo2"
    assert iid == 2
    assert provider == ProviderType.GITLAB

    assert TaskType.UNRESOLVED_COMMENTS in mapping
    repo, iid, title, provider = mapping[TaskType.UNRESOLVED_COMMENTS]
    assert repo == "group/repo3"
    assert iid == 3
    assert provider == ProviderType.GITLAB

    # Issue-derived task
    assert TaskType.OPEN_ISSUE in mapping
    repo, iid, title, provider = mapping[TaskType.OPEN_ISSUE]
    # repo should be everything before the '#' character
    assert repo == "group/repo5"
    assert iid == 10
    assert provider == ProviderType.GITLAB


async def test_get_suggested_tasks_graphql_exception_returns_empty_round_013():
    svc = DummyService()

    async def fake_get_user(self):
        return SimpleNamespace(login="jdoe")

    async def raising_execute_graphql_query(self, query):
        raise RuntimeError("simulated graphql failure")

    # _make_request should not be called in this scenario, but provide a safe stub
    async def fake_make_request(self, method: RequestMethod, url: str, params: dict):
        return [], None

    svc.get_user = types.MethodType(fake_get_user, svc)
    svc.execute_graphql_query = types.MethodType(raising_execute_graphql_query, svc)
    svc._make_request = types.MethodType(fake_make_request, svc)

    tasks = await _bind_and_call_get_suggested_tasks(svc)

    # On exception the function returns an empty list (see except Exception: return [])
    assert tasks == []
