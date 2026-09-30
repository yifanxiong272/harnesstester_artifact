# file: openhands/integrations/azure_devops/service/features.py:40-141
# asked: {"lines": [45, 46, 47, 50, 51, 54, 55, 57, 59, 62, 63, 65, 67, 68, 69, 70, 73, 74, 75, 78, 79, 80, 84, 85, 86, 89, 90, 91, 95, 96, 97, 100, 101, 102, 107, 108, 110, 111, 114, 115, 118, 121, 122, 123, 124, 126, 128, 129, 132, 133, 134, 137, 139, 141], "branches": [[54, 55], [54, 141], [67, 68], [67, 107], [73, 74], [73, 84], [84, 85], [84, 95], [95, 67], [95, 96], [121, 54], [121, 122]]}
# gained: {"lines": [45, 46, 47, 50, 51, 54, 55, 57, 59, 62, 63, 65, 67, 68, 69, 70, 73, 74, 75, 78, 79, 80, 84, 85, 86, 89, 90, 91, 95, 96, 97, 100, 101, 102, 107, 108, 110, 111, 114, 115, 118, 121, 122, 123, 124, 126, 128, 129, 132, 133, 134, 137, 139, 141], "branches": [[54, 55], [54, 141], [67, 68], [67, 107], [73, 74], [73, 84], [84, 85], [84, 95], [95, 96], [121, 54], [121, 122]]}

import pytest
import types
from typing import Any

from openhands.integrations.azure_devops.service.features import AzureDevOpsFeaturesMixin
from openhands.integrations.service_types import (
    ProviderType,
    RequestMethod,
    SuggestedTask,
    TaskType,
)


class DummyAzure(AzureDevOpsFeaturesMixin):
    def __init__(self):
        # minimal attributes used by the mixin method
        self.organization = "org"

    @property
    def base_url(self) -> str:
        return "https://dev.azure.com/org"

    async def get_user(self):
        # return an object with .id attribute
        return types.SimpleNamespace(id="user-1")

    def _encode_url_component(self, s: str) -> str:
        # simple encoder to match expectations in the method under test
        return s.replace(" ", "%20")

    async def _make_request(self, url: str, params: Any = None, method: Any = None):
        # projects list
        if url == f"{self.base_url}/_apis/projects?api-version=7.1":
            return ({"value": [{"name": "Project One"}, {"name": "Project Two"}, {"name": "Bad Project"}]}, None)

        # pull requests for a project
        if "/_apis/git/pullrequests" in url:
            if "Bad%20Project" in url:
                # simulate access error for Bad Project to trigger the except/continue branch
                raise Exception("access denied")
            if "Project%20One" in url:
                # one PR with merge conflicts
                pr = {
                    "value": [
                        {
                            "repository": {"name": "RepoA"},
                            "pullRequestId": 1,
                            "title": "Fix A",
                            "mergeStatus": "conflicts",
                        }
                    ]
                }
                return (pr, None)
            if "Project%20Two" in url:
                # one failed check and one unresolved comments
                pr = {
                    "value": [
                        {
                            "repository": {"name": "RepoB"},
                            "pullRequestId": 2,
                            "title": "Fix B",
                            "status": "failed",
                        },
                        {
                            "repository": {"name": "RepoC"},
                            "pullRequestId": 3,
                            "title": "Comment C",
                            "hasUnresolvedComments": True,
                        },
                    ]
                }
                return (pr, None)
            # default empty
            return ({"value": []}, None)

        # WIQL query (work items list)
        if "/_apis/wit/wiql" in url and method == RequestMethod.POST:
            if "Project%20One" in url:
                return ({"workItems": [{"id": 101}]}, None)
            if "Project%20Two" in url:
                return ({"workItems": [{"id": 102}]}, None)
            return ({"workItems": []}, None)

        # work item details
        if "/_apis/wit/workitems/" in url:
            # extract id from URL
            # url format: {base}/{project_enc}/_apis/wit/workitems/{id}?api-version=7.1
            try:
                id_part = url.split("/_apis/wit/workitems/")[1]
                work_id_str = id_part.split("?")[0]
                work_id = int(work_id_str)
            except Exception:
                work_id = 0
            return ({"fields": {"System.Title": f"WI {work_id}"}}, None)

        # fallback empty
        return ({}, None)


@pytest.mark.asyncio
async def test_get_suggested_tasks_all_branches():
    dummy = DummyAzure()
    tasks = await dummy.get_suggested_tasks()

    # Expecting:
    # - Project One: 1 PR (merge conflicts) + 1 work item (101)
    # - Project Two: 2 PRs (failed, unresolved) + 1 work item (102)
    # - Bad Project: raises inside try and is skipped
    # Total tasks: 1 + 1 + 2 + 1 = 5
    assert isinstance(tasks, list)
    assert len(tasks) == 5

    # Collect types and identifiers for assertions
    types_found = [t.task_type for t in tasks]
    issue_numbers = [t.issue_number for t in tasks]
    repos = [t.repo for t in tasks]
    titles = [t.title for t in tasks]

    # Check PR-related task types present
    assert TaskType.MERGE_CONFLICTS in types_found
    assert TaskType.FAILING_CHECKS in types_found
    assert TaskType.UNRESOLVED_COMMENTS in types_found
    # Check work item (open issue) present
    assert TaskType.OPEN_ISSUE in types_found

    # Check specific issue numbers for work items
    assert any(t.task_type == TaskType.OPEN_ISSUE and t.issue_number == 101 for t in tasks)
    assert any(t.task_type == TaskType.OPEN_ISSUE and t.issue_number == 102 for t in tasks)

    # Check repo formatting for PRs: should include organization/project/repo
    assert any(t.task_type == TaskType.MERGE_CONFLICTS and t.repo == "org/Project One/RepoA" for t in tasks)
    assert any(t.task_type == TaskType.FAILING_CHECKS and t.repo == "org/Project Two/RepoB" for t in tasks)
    assert any(t.task_type == TaskType.UNRESOLVED_COMMENTS and t.repo == "org/Project Two/RepoC" for t in tasks)

    # Titles propagated from mocked responses
    assert any(t.title == "Fix A" for t in tasks)
    assert any(t.title == "Fix B" for t in tasks)
    assert any(t.title == "Comment C" for t in tasks)
    assert any(t.title == "WI 101" for t in tasks)
    assert any(t.title == "WI 102" for t in tasks)
