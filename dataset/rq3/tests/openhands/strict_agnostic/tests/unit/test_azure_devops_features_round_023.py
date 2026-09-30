import pytest
from types import SimpleNamespace

from openhands.integrations.azure_devops.service.features import AzureDevOpsFeaturesMixin
from openhands.integrations.service_types import TaskType, ProviderType


class DummyClient_round_023(AzureDevOpsFeaturesMixin):
    """Minimal client that overrides network calls for deterministic testing."""

    # Diagnosis revealed that AzureDevOpsMixinBase declares abstract attributes/properties
    # that must be present at the class level (not just set in __init__). Provide defaults
    # here so the class is instantiable.
    base_url = "https://dev.azure.example"
    organization = "orgX"

    def __init__(self, base_url: str = None, organization: str = None):
        # allow overrides but keep class-level defaults so ABC requirements are satisfied
        if base_url is not None:
            self.base_url = base_url
        if organization is not None:
            self.organization = organization

    async def get_user(self):
        # Return a simple user object with an id attribute
        return SimpleNamespace(id="user-1")

    def _encode_url_component(self, val: str) -> str:
        # simple deterministic encoding
        return val.replace(" ", "%20")

    async def _make_request(self, url, params=None, method=None):
        """Return deterministic responses based on the requested URL.

        This function purposefully does not perform any network I/O.
        It inspects the URL to return the appropriate fake responses used
        by get_suggested_tasks.
        """
        # Projects list
        if url == f"{self.base_url}/_apis/projects?api-version=7.1":
            return {"value": [{"name": "ProjA"}, {"name": "ProjB"}, {"name": "BrokenProj"}]}, {}

        # Simulate a project that raises an exception to trigger the except/continue path
        if "BrokenProj" in url:
            raise Exception("project inaccessible")

        # Pull requests for ProjA: one with merge conflicts, one with unresolved comments
        if "/ProjA/" in url and "pullrequests" in url:
            return {
                "value": [
                    {
                        "repository": {"name": "repo1"},
                        "pullRequestId": 1,
                        "title": "Fix A",
                        "mergeStatus": "conflicts",
                    },
                    {
                        "repository": {"name": "repo1"},
                        "pullRequestId": 2,
                        "title": "Commented",
                        "hasUnresolvedComments": True,
                    },
                ]
            }, {}

        # Pull requests for ProjB: one failing check
        if "/ProjB/" in url and "pullrequests" in url:
            return {
                "value": [
                    {
                        "repository": {"name": "repoB"},
                        "pullRequestId": 3,
                        "title": "Failing",
                        "status": "failed",
                    }
                ]
            }, {}

        # WIQL query: return a single work item reference for ProjA
        if "_apis/wit/wiql" in url:
            if "/ProjA/" in url:
                return {"workItems": [{"id": 100}]}, {}
            return {"workItems": []}, {}

        # Work item details for id 100
        if "_apis/wit/workitems/100" in url:
            return {"fields": {"System.Title": "Task 100"}}, {}

        # Default empty response
        return {}, {}


@pytest.mark.asyncio
async def test_get_suggested_tasks_various_prs_round_023():
    """Exercise several PR and work item branches deterministically.

    This test covers:
    - merge conflicts branch
    - failing checks branch
    - unresolved comments branch
    - work item -> OPEN_ISSUE branch
    - per-project exception handling (BrokenProj)
    """
    client = DummyClient_round_023()

    tasks = await client.get_suggested_tasks()

    # We expect four tasks created: merge conflict, unresolved comments, failing checks, open issue
    assert isinstance(tasks, list)
    assert len(tasks) == 4

    # Collect types and map by issue_number for easier assertions
    by_issue = {t.issue_number: t for t in tasks}

    # Merge conflict PR (id=1)
    t1 = by_issue.get(1)
    assert t1 is not None, "expected task for PR 1"
    assert t1.task_type == TaskType.MERGE_CONFLICTS
    assert t1.git_provider == ProviderType.AZURE_DEVOPS
    assert "ProjA" in t1.repo and "repo1" in t1.repo
    assert t1.title == "Fix A"

    # Unresolved comments PR (id=2)
    t2 = by_issue.get(2)
    assert t2 is not None, "expected task for PR 2"
    assert t2.task_type == TaskType.UNRESOLVED_COMMENTS
    assert "ProjA" in t2.repo and "repo1" in t2.repo
    assert t2.title == "Commented"

    # Failing checks PR (id=3)
    t3 = by_issue.get(3)
    assert t3 is not None, "expected task for PR 3"
    assert t3.task_type == TaskType.FAILING_CHECKS
    assert "ProjB" in t3.repo and "repoB" in t3.repo
    assert t3.title == "Failing"

    # Work item open issue (id=100)
    t100 = by_issue.get(100)
    assert t100 is not None, "expected task for work item 100"
    assert t100.task_type == TaskType.OPEN_ISSUE
    # repo for work items is organization/project
    assert t100.repo.endswith("ProjA")
    assert t100.title == "Task 100"
