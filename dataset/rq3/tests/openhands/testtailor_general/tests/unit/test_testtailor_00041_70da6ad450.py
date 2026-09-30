import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.service_types')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Test SuggestedTask.get_provider_terms returns GitLab mapping for GITLAB provider."""
        suggested_task = SuggestedTask(
            git_provider=ProviderType.GITLAB,
            task_type=TaskType.OPEN_ISSUE,
            repo='owner/repo',
            issue_number=1,
            title='Test GitLab terms',
        )

        terms = suggested_task.get_provider_terms()

        expected = {
            'requestType': 'Merge Request',
            'requestTypeShort': 'MR',
            'apiName': 'GitLab API',
            'tokenEnvVar': 'GITLAB_TOKEN',
            'ciSystem': 'CI pipelines',
            'ciProvider': 'GitLab',
            'requestVerb': 'merge request',
        }

        self.assertEqual(terms, expected)
