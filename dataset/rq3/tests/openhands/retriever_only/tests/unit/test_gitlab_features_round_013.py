import asyncio
from types import SimpleNamespace
import pytest

from openhands.integrations.gitlab.service.features import GitLabFeaturesMixin
from openhands.integrations.service_types import (
    SuggestedTask,
    TaskType,
    ProviderType,
    RequestMethod,
)

# Helper to call the unbound async method with a fake self
async def _call_get_suggested_tasks_with(self_obj):
    # call the function as defined on the class to avoid needing an actual initialized instance
    return await GitLabFeaturesMixin.get_suggested_tasks(self_obj)

class DummySelf:
    def __init__(self, base_url="https://gitlab.local/api"):
        self.BASE_URL = base_url

        # These will be set by tests as needed
        self._graphql_response = {'currentUser': {}}
        self._issues_response = []
        self._should_raise_graphql = False

    async def get_user(self):
        # Return an object with a login attribute to exercise username extraction
        return SimpleNamespace(login="testuser")

    async def execute_graphql_query(self, query):
        if self._should_raise_graphql:
            raise RuntimeError("graphql failed")
        # Return the configured graphql response
        return self._graphql_response

    async def _make_request(self, method: RequestMethod, url: str, params: dict):
        # Return a tuple like (issues_response, status_or_meta)
        return (self._issues_response, None)


@pytest.mark.asyncio
async def test_merge_request_conflicts_round_013():
    """MR with conflicts should produce MERGE_CONFLICTS SuggestedTask and not rely on issues."""
    dummy = DummySelf()

    dummy._graphql_response = {
        'currentUser': {
            'authoredMergeRequests': {
                'nodes': [
                    {
                        'iid': 42,
                        'title': 'Conflicting MR',
                        'project': {'fullPath': 'group/repo'},
                        'conflicts': True,
                        'pipelines': {'nodes': []},
                        'discussions': {'nodes': []},
                    }
                ]
            }
        }
    }
    dummy._issues_response = []

    tasks = await _call_get_suggested_tasks_with(dummy)

    # Expect exactly one task and it should be MERGE_CONFLICTS
    assert isinstance(tasks, list)
    assert len(tasks) == 1
    t = tasks[0]
    assert isinstance(t, SuggestedTask)
    assert t.task_type == TaskType.MERGE_CONFLICTS
    assert t.git_provider == ProviderType.GITLAB
    assert t.repo == 'group/repo'
    assert t.issue_number == 42
    assert t.title == 'Conflicting MR'


@pytest.mark.asyncio
async def test_merge_request_failing_checks_round_013():
    """MR with a pipeline node status FAILED should produce FAILING_CHECKS."""
    dummy = DummySelf()
    dummy._graphql_response = {
        'currentUser': {
            'authoredMergeRequests': {
                'nodes': [
                    {
                        'iid': 99,
                        'title': 'Broken CI MR',
                        'project': {'fullPath': 'org/project'},
                        'conflicts': False,
                        'pipelines': {'nodes': [{'status': 'FAILED'}]},
                        'discussions': {'nodes': []},
                    }
                ]
            }
        }
    }
    dummy._issues_response = []

    tasks = await _call_get_suggested_tasks_with(dummy)

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.FAILING_CHECKS
    assert t.repo == 'org/project'
    assert t.issue_number == 99
    assert t.title == 'Broken CI MR'


@pytest.mark.asyncio
async def test_merge_request_unresolved_comments_round_013():
    """MR with an unresolved, resolvable note should produce UNRESOLVED_COMMENTS."""
    dummy = DummySelf()
    dummy._graphql_response = {
        'currentUser': {
            'authoredMergeRequests': {
                'nodes': [
                    {
                        'iid': 7,
                        'title': 'Needs review',
                        'project': {'fullPath': 'a/b'},
                        'conflicts': False,
                        'pipelines': {'nodes': []},
                        'discussions': {
                            'nodes': [
                                {
                                    'notes': {
                                        'nodes': [
                                            {'resolvable': True, 'resolved': False}
                                        ]
                                    }
                                }
                            ]
                        },
                    }
                ]
            }
        }
    }
    dummy._issues_response = []

    tasks = await _call_get_suggested_tasks_with(dummy)

    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.UNRESOLVED_COMMENTS
    assert t.repo == 'a/b'
    assert t.issue_number == 7
    assert t.title == 'Needs review'


@pytest.mark.asyncio
async def test_issue_processing_and_username_round_013():
    """When there are no authored MRs, assigned issues are converted to OPEN_ISSUE and repo parsing is applied."""
    dummy = DummySelf()
    dummy._graphql_response = {'currentUser': {'authoredMergeRequests': {'nodes': []}}}

    # Issue with references.full containing '#', expect repo portion before '#'
    dummy._issues_response = [
        {
            'iid': 123,
            'title': 'An open issue',
            'references': {'full': 'mygroup/myrepo#123'},
        }
    ]

    tasks = await _call_get_suggested_tasks_with(dummy)

    # Should produce exactly one OPEN_ISSUE SuggestedTask
    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_type == TaskType.OPEN_ISSUE
    assert t.repo == 'mygroup/myrepo'
    assert t.issue_number == 123
    assert t.title == 'An open issue'
    assert t.git_provider == ProviderType.GITLAB


@pytest.mark.asyncio
async def test_execute_graphql_raises_returns_empty_round_013():
    """If execute_graphql_query raises, the function should catch and return an empty list."""
    dummy = DummySelf()
    dummy._should_raise_graphql = True

    # Also supply an issues list to ensure exception short-circuits and returns []
    dummy._issues_response = [
        {'iid': 1, 'title': 'ignored', 'references': {'full': 'x/y#1'}}
    ]

    tasks = await _call_get_suggested_tasks_with(dummy)
    assert tasks == []
