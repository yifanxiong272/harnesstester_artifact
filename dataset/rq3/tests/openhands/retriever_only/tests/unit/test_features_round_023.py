import asyncio
from types import SimpleNamespace
import pytest

from openhands.integrations.azure_devops.service import features as features_mod

# A small test helper that mimics the mixin but provides controllable responses
class FakeAzureDevOps(features_mod.AzureDevOpsFeaturesMixin):
    def __init__(self, base_url, organization, behaviour):
        # behaviour: a dict describing what responses to return for different endpoints
        # store as private attributes; expose via properties to satisfy abstract properties
        self._base_url = base_url
        self._organization = organization
        self._behaviour = behaviour

    # Implement abstract properties required by the base class
    @property
    def base_url(self):
        return self._base_url

    @property
    def organization(self):
        return self._organization

    async def get_user(self):
        # Return an object with an id attribute as expected by the implementation
        return SimpleNamespace(id=self._behaviour.get('user_id', 'user-1'))

    def _encode_url_component(self, v: str) -> str:
        # keep simple and deterministic
        return str(v).replace(' ', '%20')

    async def _make_request(self, url, params=None, method=None):
        # Determine response by inspecting the URL and method
        # Simulate raising exceptions for certain test behaviours
        if self._behaviour.get('raise_on') and any(token in url for token in self._behaviour['raise_on']):
            raise Exception('simulated request failure')

        if '/_apis/projects' in url and 'git/pullrequests' not in url and '/wit/' not in url:
            # Projects listing
            return (self._behaviour.get('projects_response', {'value': []}), None)

        if '/_apis/git/pullrequests' in url:
            return (self._behaviour.get('pull_requests_response', {'value': []}), None)

        if '/_apis/wit/wiql' in url and method == features_mod.RequestMethod.POST:
            return (self._behaviour.get('work_items_response', {'workItems': []}), None)

        if '/_apis/wit/workitems/' in url:
            return (self._behaviour.get('work_item_detail', {}), None)

        # default safe response
        return ({}, None)


@pytest.mark.asyncio
async def test_pr_conflicts_round_023():
    """A PR with mergeStatus 'conflicts' should produce a MERGE_CONFLICTS SuggestedTask."""
    behaviour = {
        'user_id': 'user-1',
        'projects_response': {'value': [{'name': 'Proj'}]},
        'pull_requests_response': {
            'value': [
                {
                    'repository': {'name': 'Repo1'},
                    'pullRequestId': 123,
                    'title': 'Conflict fix',
                    'mergeStatus': 'conflicts',
                }
            ]
        },
        'work_items_response': {'workItems': []},
    }

    inst = FakeAzureDevOps('https://dev.azure.com/org', 'org', behaviour)
    tasks = await inst.get_suggested_tasks()

    # One task should be returned and it should represent merge conflicts
    assert len(tasks) == 1
    t = tasks[0]
    assert isinstance(t, features_mod.SuggestedTask)
    assert t.task_type == features_mod.TaskType.MERGE_CONFLICTS
    assert t.git_provider == features_mod.ProviderType.AZURE_DEVOPS
    # repo should include organization, project and repository name
    assert t.repo == 'org/Proj/Repo1'
    assert t.issue_number == 123
    assert t.title == 'Conflict fix'


@pytest.mark.asyncio
async def test_pr_failed_unresolved_and_workitem_round_023():
    """PRs with 'failed' status and unresolved comments plus a work item should be reported."""
    behaviour = {
        'user_id': 'user-42',
        'projects_response': {'value': [{'name': 'My Project'}]},
        'pull_requests_response': {
            'value': [
                {
                    'repository': {'name': 'RepoA'},
                    'pullRequestId': 10,
                    'title': 'Broken checks',
                    'status': 'failed',
                },
                {
                    'repository': {'name': 'RepoB'},
                    'pullRequestId': 11,
                    'title': 'Some discussion',
                    'hasUnresolvedComments': True,
                }
            ]
        },
        'work_items_response': {'workItems': [{'id': 77}]},
        'work_item_detail': {
            'fields': {'System.Title': 'Investigate bug'}
        },
    }

    inst = FakeAzureDevOps('https://dev.azure.com/org', 'org', behaviour)
    tasks = await inst.get_suggested_tasks()

    # Expect three tasks: failing checks, unresolved comments, and an open issue (work item)
    # Order: PRs discovered first (2), then work items (1)
    assert len(tasks) == 3

    types = [t.task_type for t in tasks]
    assert features_mod.TaskType.FAILING_CHECKS in types
    assert features_mod.TaskType.UNRESOLVED_COMMENTS in types
    assert features_mod.TaskType.OPEN_ISSUE in types

    # Verify the work item task has the expected title and repo structure (organization/project)
    work_tasks = [t for t in tasks if t.task_type == features_mod.TaskType.OPEN_ISSUE]
    assert len(work_tasks) == 1
    wt = work_tasks[0]
    assert wt.issue_number == 77
    assert wt.title == 'Investigate bug'
    assert wt.repo == 'org/My Project'


@pytest.mark.asyncio
async def test_project_exception_skips_round_023():
    """If a project's requests raise an exception, it should be skipped (no crash) and continue."""
    behaviour = {
        'user_id': 'user-x',
        'projects_response': {'value': [{'name': 'BadProj'}]},
        # Simulate that any call touching BadProj will raise in _make_request
        'raise_on': ['BadProj'],
    }

    inst = FakeAzureDevOps('https://dev.azure.com/org', 'org', behaviour)
    tasks = await inst.get_suggested_tasks()

    # The failing project should simply be skipped and result in an empty tasks list
    assert tasks == []
