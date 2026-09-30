import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.azuredevops_provider')
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
        """Ensure that providing pr_url to __init__ calls set_pr and parses URL correctly."""
        pr_url = "https://dev.azure.com/org/project/_git/repo/pullrequest/42"

        mock_client = MagicMock()
        mock_board = MagicMock()
        mock_pr = MagicMock()
        mock_client.get_pull_request_by_id.return_value = mock_pr

        with patch.object(AzureDevopsProvider, "_get_azure_devops_client", return_value=(mock_client, mock_board)) as mock_get_client:
            provider = AzureDevopsProvider(pr_url=pr_url)

            # verify parsed values from the PR URL
            self.assertEqual(provider.pr_url, pr_url)
            self.assertEqual(provider.workspace_slug, "project")
            self.assertEqual(provider.repo_slug, "repo")
            self.assertEqual(provider.pr_num, 42)

            # provider.pr should be set from the mocked client's get_pull_request_by_id
            self.assertIs(provider.pr, mock_pr)

            # ensure _get_pr invoked the underlying client with expected args
            mock_client.get_pull_request_by_id.assert_called_once_with(pull_request_id=42, project="project")
            mock_get_client.assert_called_once()
