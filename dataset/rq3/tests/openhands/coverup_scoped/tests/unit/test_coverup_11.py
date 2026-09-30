# file: openhands/integrations/gitlab/service/features.py:50-180
# asked: {"lines": [58, 59, 62, 96, 97, 100, 101, 104, 105, 106, 107, 108, 111, 114, 115, 117, 118, 119, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 137, 138, 139, 141, 142, 143, 144, 149, 150, 151, 152, 153, 156, 157, 161, 162, 163, 165, 166, 168, 169, 172, 173, 174, 178, 179, 180], "branches": [[105, 106], [105, 149], [114, 115], [114, 116], [116, 121], [116, 124], [125, 126], [125, 133], [126, 127], [126, 130], [127, 126], [127, 128], [130, 125], [130, 131], [133, 134], [133, 137], [137, 105], [137, 138], [161, 162], [161, 178]]}
# gained: {"lines": [58, 59, 62, 96, 97, 100, 101, 104, 105, 106, 107, 108, 111, 114, 115, 117, 118, 119, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 137, 138, 139, 141, 142, 143, 144, 149, 150, 151, 152, 153, 156, 157, 161, 162, 163, 165, 166, 168, 169, 172, 173, 174, 178, 179, 180], "branches": [[105, 106], [105, 149], [114, 115], [114, 116], [116, 121], [116, 124], [125, 126], [125, 133], [126, 127], [127, 128], [130, 131], [133, 134], [133, 137], [137, 105], [137, 138], [161, 162], [161, 178]]}

import pytest
from types import SimpleNamespace

import asyncio

from openhands.integrations.gitlab.service.features import GitLabFeaturesMixin
from openhands.integrations.service_types import ProviderType, RequestMethod, SuggestedTask, TaskType


class DummyGitLabClient(GitLabFeaturesMixin):
    # Minimal attributes required by the mixin
    BASE_URL = "https://gitlab.example/api/v4"


@pytest.mark.asyncio
async def test_get_suggested_tasks_various_mrs_and_issues():
    client = DummyGitLabClient()

    async def fake_get_user():
        return SimpleNamespace(login="testuser")

    async def fake_execute_graphql_query(query):
        # Four MRs: one conflicts, one failing pipeline, one with unresolved comments, one plain open PR
        return {
            "currentUser": {
                "authoredMergeRequests": {
                    "nodes": [
                        {
                            "id": "gid://1",
                            "iid": 1,
                            "title": "Conflicting MR",
                            "project": {"fullPath": "group/conflict-repo"},
                            "conflicts": True,
                            "mergeStatus": "cannot_be_merged",
                            "pipelines": {"nodes": []},
                            "discussions": {"nodes": []},
                        },
                        {
                            "id": "gid://2",
                            "iid": 2,
                            "title": "Failing Pipeline MR",
                            "project": {"fullPath": "group/fail-repo"},
                            "conflicts": False,
                            "mergeStatus": "can_be_merged",
                            "pipelines": {"nodes": [{"status": "FAILED"}]},
                            "discussions": {"nodes": []},
                        },
                        {
                            "id": "gid://3",
                            "iid": 3,
                            "title": "Unresolved Comments MR",
                            "project": {"fullPath": "group/unresolved-repo"},
                            "conflicts": False,
                            "mergeStatus": "can_be_merged",
                            "pipelines": {"nodes": []},
                            "discussions": {
                                "nodes": [
                                    {
                                        "notes": {
                                            "nodes": [
                                                {"resolvable": True, "resolved": False},
                                            ]
                                        }
                                    }
                                ]
                            },
                        },
                        {
                            "id": "gid://4",
                            "iid": 4,
                            "title": "Plain Open MR",
                            "project": {"fullPath": "group/plain-repo"},
                            "conflicts": False,
                            "mergeStatus": "can_be_merged",
                            "pipelines": {"nodes": []},
                            "discussions": {"nodes": []},
                        },
                    ]
                }
            }
        }

    async def fake_make_request(method: RequestMethod, url: str, params: dict):
        # Validate that the method and URL constructed match expectations
        assert method == RequestMethod.GET
        assert url == f"{client.BASE_URL}/issues"
        assert params["assignee_username"] == "testuser"
        assert params["state"] == "opened"
        assert params["scope"] == "assigned_to_me"

        issues = [
            {
                "references": {"full": "group/issue-repo#10"},
                "iid": 10,
                "title": "Assigned Issue 10",
            },
            {
                "references": {"full": "group/another-repo#42"},
                "iid": 42,
                "title": "Assigned Issue 42",
            },
        ]
        # return tuple (response, status) as the code expects two values
        return issues, 200

    # Attach the fake async methods to our instance
    client.get_user = fake_get_user
    client.execute_graphql_query = fake_execute_graphql_query
    client._make_request = fake_make_request

    tasks = await client.get_suggested_tasks()

    # We expect 3 MR-derived tasks (conflicts, failing checks, unresolved comments) + 2 issues = 5
    assert isinstance(tasks, list)
    assert len(tasks) == 5

    # Map by (task_type, issue_number) for easy assertions
    seen = {(t.task_type, t.issue_number, t.repo, t.title) for t in tasks}

    expected = {
        (TaskType.MERGE_CONFLICTS, 1, "group/conflict-repo", "Conflicting MR"),
        (TaskType.FAILING_CHECKS, 2, "group/fail-repo", "Failing Pipeline MR"),
        (TaskType.UNRESOLVED_COMMENTS, 3, "group/unresolved-repo", "Unresolved Comments MR"),
        (TaskType.OPEN_ISSUE, 10, "group/issue-repo", "Assigned Issue 10"),
        (TaskType.OPEN_ISSUE, 42, "group/another-repo", "Assigned Issue 42"),
    }

    assert seen == expected

    # Also check git_provider correctness
    for t in tasks:
        assert t.git_provider == ProviderType.GITLAB


@pytest.mark.asyncio
async def test_get_suggested_tasks_handles_exceptions_and_returns_empty():
    client = DummyGitLabClient()

    async def fake_get_user():
        return SimpleNamespace(login="testuser2")

    async def raising_execute_graphql_query(query):
        raise RuntimeError("GraphQL failure")

    # _make_request should not be called, but provide it anyway to ensure no side effects
    async def fake_make_request(method: RequestMethod, url: str, params: dict):
        pytest.fail("._make_request should not be called when execute_graphql_query raises")

    client.get_user = fake_get_user
    client.execute_graphql_query = raising_execute_graphql_query
    client._make_request = fake_make_request

    tasks = await client.get_suggested_tasks()
    assert tasks == []
