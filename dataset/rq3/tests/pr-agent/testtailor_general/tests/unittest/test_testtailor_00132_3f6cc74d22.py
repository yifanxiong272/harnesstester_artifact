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
        """Verify that initializing GithubProvider with an issue URL sets issue_main via _get_issue_handle"""
        # patch the methods used during __init__ to avoid external dependencies
        orig_get_github_client = GithubProvider._get_github_client
        orig_get_issue_handle = GithubProvider._get_issue_handle
        try:
            GithubProvider._get_github_client = lambda self: object()
            # return a simple sentinel to verify it was assigned
            GithubProvider._get_issue_handle = lambda self, url: {"mock_issue": True, "url": url}

            pr_url = "https://api.github.com/repos/example_owner/example_repo/issues/123"
            provider = GithubProvider(pr_url=pr_url)

            self.assertIsNotNone(provider.issue_main)
            self.assertEqual(provider.issue_main, {"mock_issue": True, "url": pr_url})
        finally:
            # restore originals
            GithubProvider._get_github_client = orig_get_github_client
            GithubProvider._get_issue_handle = orig_get_issue_handle
