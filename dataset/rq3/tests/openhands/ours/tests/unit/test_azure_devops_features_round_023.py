import pytest
from types import SimpleNamespace

from openhands.integrations.azure_devops.service import features as features_mod
from openhands.integrations.service_types import RequestMethod, TaskType

AzureDevOpsFeaturesMixin = features_mod.AzureDevOpsFeaturesMixin

class DummyFeatures(AzureDevOpsFeaturesMixin):
    """Minimal subclass that overrides network and env interactions deterministically.

    Implements the abstract base_url property required by the mixin.
    """
    def __init__(self, base_url="https://dev.azure.com/org", organization="org"):
        # store backing attribute for the base_url property
        self._base_url = base_url
        self.organization = organization
        self._seen_requests = []

    @property
    def base_url(self):
        # satisfy abstract property on the mixin
        return self._base_url

    async def get_user(self):
        # return a simple object with an id attribute (the code only uses .id)
        return SimpleNamespace(id="user-1")

    def _encode_url_component(self, component: str) -> str:
        # The real implementation is used synchronously in the function under test
        return component.replace(" ", "%20")

    async def _make_request(self, url, params=None, method=None):
        # Record the call for later inspection and return deterministic payloads
        self._seen_requests.append({"url": url, "params": params, "method": method})

        # Projects list request
        if url.endswith("/_apis/projects?api-version=7.1"):
            return {"value": [{"name": "My Project"}]}, None

        # Pull requests for the project
        if "/_apis/git/pullrequests" in url:
            return {
                "value": [
                    {
                        "repository": {"name": "repo1"},
                        "pullRequestId": 123,
                        "title": "Fix bug",
                        "mergeStatus": "conflicts",
                    }
                ]
            }, None

        # WIQL POST request returning work item references
        if url.endswith("/_apis/wit/wiql?api-version=7.1") and method == RequestMethod.POST:
            return {"workItems": [{"id": 42}]}, None

        # Work item details
        if "/_apis/wit/workitems/42" in url:
            return {"fields": {"System.Title": "Work item title"}}, None

        raise RuntimeError(f"Unexpected request: {url} {method} {params}")


class DummyFeaturesForFailure(DummyFeatures):
    async def _make_request(self, url, params=None, method=None):
        # Simulate a failure when iterating a project to trigger the except: continue path
        if "/_apis/git/pullrequests" in url:
            raise RuntimeError("simulated access error for project")
        # Delegate other calls to parent
        return await super()._make_request(url, params=params, method=method)


@pytest.mark.asyncio
async def test_get_suggested_tasks_conflict_and_work_item_round_023():
    """Covers: project iteration, PR 'conflicts' branch, WIQL POST and work item details."""
    inst = DummyFeatures()

    tasks = await inst.get_suggested_tasks()

    # Expect two suggested tasks: one from the PR conflict and one from the work item
    assert isinstance(tasks, list)
    assert len(tasks) == 2

    pr_task = tasks[0]
    wi_task = tasks[1]

    # PR conflict task assertions
    assert pr_task.task_type == TaskType.MERGE_CONFLICTS
    assert pr_task.repo == f"{inst.organization}/My Project/repo1"
    assert pr_task.issue_number == 123
    assert pr_task.title == "Fix bug"

    # Work item task assertions
    assert wi_task.task_type == TaskType.OPEN_ISSUE
    assert wi_task.repo == f"{inst.organization}/My Project"
    assert wi_task.issue_number == 42
    assert wi_task.title == "Work item title"


@pytest.mark.asyncio
async def test_get_suggested_tasks_handles_project_errors_round_023():
    """Covers: exception during project processing (should be skipped, not raise).

    We simulate a failing _make_request for PR retrieval so the mixin's except block is hit
    and the function continues gracefully, returning an empty list (no tasks collected).
    """
    inst = DummyFeaturesForFailure()

    # The projects response is still provided by the base logic, but processing the
    # project's PRs will raise and should be skipped.
    tasks = await inst.get_suggested_tasks()

    # No tasks should be returned because the only project's processing raised
    assert isinstance(tasks, list)
    assert tasks == []


@pytest.mark.asyncio
async def test_get_suggested_tasks_no_projects_round_023():
    """Covers: no projects returned (skips the for-loop entirely).

    Ensure that when the projects list is empty, the function returns an empty list
    without errors (branch that goes from loop directly to return).
    """

    class NoProjects(DummyFeatures):
        async def _make_request(self, url, params=None, method=None):
            if url.endswith("/_apis/projects?api-version=7.1"):
                return {"value": []}, None
            # Any other call is unexpected in this scenario
            raise RuntimeError("Unexpected call")

    inst = NoProjects()
    tasks = await inst.get_suggested_tasks()
    assert tasks == []
