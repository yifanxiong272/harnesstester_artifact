import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.github_provider')
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
        """Ensure that when initialized with an issue URL, GithubProvider calls _get_issue_handle and sets issue_main."""
        pr_url = "https://github.com/example_owner/example_repo/issues/123"

        mock_client = unittest.mock.Mock()
        mock_issue = unittest.mock.Mock()

        # Patch _get_github_client so __init__ doesn't try to authenticate or call real GitHub.
        with unittest.mock.patch.object(GithubProvider, "_get_github_client", return_value=mock_client) as mock_get_client, \
             unittest.mock.patch.object(GithubProvider, "_get_issue_handle", return_value=mock_issue) as mock_get_issue:

            provider = GithubProvider(pr_url=pr_url)

            # _get_github_client should have been called during initialization
            mock_get_client.assert_called_once()

            # _get_issue_handle should be called with the provided issue URL and its result assigned
            mock_get_issue.assert_called_once_with(pr_url)
            self.assertIs(provider.issue_main, mock_issue)
