# file: openhands/integrations/gitlab/service/features.py:50-180
# asked: {"lines": [58, 59, 62, 96, 97, 100, 101, 104, 105, 106, 107, 108, 111, 114, 115, 117, 118, 119, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 137, 138, 139, 141, 142, 143, 144, 149, 150, 151, 152, 153, 156, 157, 161, 162, 163, 165, 166, 168, 169, 172, 173, 174, 178, 179, 180], "branches": [[105, 106], [105, 149], [114, 115], [114, 116], [116, 121], [116, 124], [125, 126], [125, 133], [126, 127], [126, 130], [127, 126], [127, 128], [130, 125], [130, 131], [133, 134], [133, 137], [137, 105], [137, 138], [161, 162], [161, 178]]}
# gained: {"lines": [58, 59, 62, 96, 97, 100, 101, 104, 105, 106, 107, 108, 111, 114, 115, 117, 118, 119, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 137, 138, 139, 141, 142, 143, 144, 149, 150, 151, 152, 153, 156, 157, 161, 162, 163, 165, 166, 168, 169, 172, 173, 174, 178, 179, 180], "branches": [[105, 106], [105, 149], [114, 115], [114, 116], [116, 121], [116, 124], [125, 126], [125, 133], [126, 127], [127, 128], [130, 131], [133, 134], [133, 137], [137, 105], [137, 138], [161, 162], [161, 178]]}

import pytest
from types import SimpleNamespace

import asyncio

from openhands.integrations.gitlab.service.features import GitLabFeaturesMixin
from openhands.integrations.service_types import TaskType, ProviderType


class DummyService(GitLabFeaturesMixin):
    BASE_URL = "https://gitlab.example/api/v4"
    GRAPHQL_URL = "https://gitlab.example/api/graphql"

    def __init__(self):
        # configure per-test responses
        self._graphql_response = None
        self._graphql_side_effect = None
        self._issues_response = []
        self._issues_headers = {}

    async def get_user(self):
        return SimpleNamespace(login="jdoe")

    async def execute_graphql_query(self, query: str, variables=None):
        if self._graphql_side_effect:
            raise self._graphql_side_effect
        return self._graphql_response

    async def _make_request(self, *args, **kwargs):
        # signature in production supports kwargs method/url/params; tests call with kwargs
        return (self._issues_response, self._issues_headers)


def make_mr_node(fullPath="org/repo", iid=1, title="MR", conflicts=False, pipeline_status=None, discussions_nodes=None):
    node = {
        "project": {"fullPath": fullPath},
        "iid": iid,
        "title": title,
        "conflicts": conflicts,
        "mergeStatus": "can_be_merged",
        "pipelines": {"nodes": []},
        "discussions": {"nodes": []},
    }
    if pipeline_status is not None:
        node["pipelines"] = {"nodes": [{"status": pipeline_status}]}
    if discussions_nodes is not None:
        node["discussions"] = {"nodes": discussions_nodes}
    return node


@pytest.mark.asyncio
async def test_get_suggested_tasks_merge_conflicts_and_issues():
    svc = DummyService()
    # MR with conflicts should become MERGE_CONFLICTS and be included
    mr = make_mr_node(fullPath="org/repo_conflict", iid=42, title="Conflict MR", conflicts=True)
    svc._graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    # one assigned issue
    svc._issues_response = [
        {"references": {"full": "org/repo_conflict#100"}, "iid": 100, "title": "Assigned issue"}
    ]

    tasks = await svc.get_suggested_tasks()

    # Expect two tasks: one MR conflict and one OPEN_ISSUE
    assert any(t.task_type == TaskType.MERGE_CONFLICTS and t.repo == "org/repo_conflict" and t.issue_number == 42 for t in tasks)
    assert any(t.task_type == TaskType.OPEN_ISSUE and t.repo == "org/repo_conflict" and t.issue_number == 100 for t in tasks)
    # Ensure provider is GitLab for both
    assert all(t.git_provider == ProviderType.GITLAB for t in tasks)


@pytest.mark.asyncio
async def test_get_suggested_tasks_failing_pipeline():
    svc = DummyService()
    # MR with failing pipeline should become FAILING_CHECKS
    mr = make_mr_node(fullPath="org/repo_ci", iid=7, title="Broken CI MR", pipeline_status="FAILED")
    svc._graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    svc._issues_response = []  # no issues

    tasks = await svc.get_suggested_tasks()

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.FAILING_CHECKS
    assert t.repo == "org/repo_ci"
    assert t.issue_number == 7
    assert t.title == "Broken CI MR"
    assert t.git_provider == ProviderType.GITLAB


@pytest.mark.asyncio
async def test_get_suggested_tasks_unresolved_comments():
    svc = DummyService()
    # MR with unresolved comment should become UNRESOLVED_COMMENTS
    discussions = [
        {"notes": {"nodes": [{"resolvable": True, "resolved": False}]}}
    ]
    mr = make_mr_node(fullPath="org/repo_comments", iid=9, title="Needs review", discussions_nodes=discussions)
    svc._graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    svc._issues_response = []

    tasks = await svc.get_suggested_tasks()

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.UNRESOLVED_COMMENTS
    assert t.repo == "org/repo_comments"
    assert t.issue_number == 9
    assert t.title == "Needs review"


@pytest.mark.asyncio
async def test_get_suggested_tasks_open_prs_are_skipped_but_issues_included():
    svc = DummyService()
    # MR that is just OPEN_PR (no conflicts, no failing pipeline, no unresolved comments) should be skipped
    mr = make_mr_node(fullPath="org/repo_open", iid=3, title="WIP MR")
    svc._graphql_response = {"currentUser": {"authoredMergeRequests": {"nodes": [mr]}}}
    # have one issue that should still be returned
    svc._issues_response = [
        {"references": {"full": "org/repo_open#55"}, "iid": 55, "title": "Assigned issue for open PR"}
    ]

    tasks = await svc.get_suggested_tasks()

    # Only issue should be present
    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.OPEN_ISSUE
    assert t.repo == "org/repo_open"
    assert t.issue_number == 55


@pytest.mark.asyncio
async def test_get_suggested_tasks_returns_empty_on_exception():
    svc = DummyService()
    # Make the GraphQL call raise to hit the exception branch
    svc._graphql_side_effect = ValueError("boom")

    tasks = await svc.get_suggested_tasks()

    assert tasks == []
