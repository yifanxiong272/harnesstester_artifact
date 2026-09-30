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
        # Prepare mocked Azure DevOps clients and a fake PR object returned by the client
        mock_azure_client = MagicMock()
        mock_board_client = MagicMock()

        pr_mock = MagicMock()
        pr_mock.description = "fake description"
        pr_mock.title = "fake title"
        # Provide commit-like objects expected by get_diff_files if later used
        pr_mock.last_merge_target_commit = MagicMock(commit_id="base_sha")
        pr_mock.last_merge_commit = MagicMock(commit_id="head_sha")

        mock_azure_client.get_pull_request_by_id.return_value = pr_mock

        # Valid Azure DevOps PR URL that matches _parse_pr_url expectations
        pr_url = "https://dev.azure.com/org/project/_git/repo/pullrequest/123"

        with patch.object(AzureDevopsProvider, "_get_azure_devops_client", return_value=(mock_azure_client, mock_board_client)):
            provider = AzureDevopsProvider(pr_url=pr_url)

            # Verify parsing and that _get_pr() was invoked and set provider.pr
            self.assertEqual(provider.workspace_slug, "project")
            self.assertEqual(provider.repo_slug, "repo")
            self.assertEqual(provider.pr_num, 123)
            self.assertIs(provider.pr, pr_mock)

            mock_azure_client.get_pull_request_by_id.assert_called_once_with(pull_request_id=123, project="project")
