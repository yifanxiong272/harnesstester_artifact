import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_server_provider')
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
        """Ensure that when bitbucket_client.get raises an exception, bitbucket_api_version is set to None."""
        bitbucket_client = MagicMock()
        # Simulate failure when querying application-properties so the constructor's try/except sets api version to None
        bitbucket_client.get.side_effect = Exception("simulated api failure")
        # Provide minimal pull request data so set_pr can complete without raising
        bitbucket_client.get_pull_request.return_value = {
            'toRef': {'latestCommit': 'deadbeef'},
            'fromRef': {'latestCommit': 'cafebabe'},
            'version': 1,
            'reviewers': [],
            'title': 'Test PR'
        }

        pr_url = "https://git.onpreminstance.com/projects/AAA/repos/my-repo/pull-requests/1"

        provider = BitbucketServerProvider(pr_url, bitbucket_client=bitbucket_client)

        # The failing get call during init should result in None for bitbucket_api_version
        self.assertIsNone(provider.bitbucket_api_version)
        # The provided client should be attached to the provider
        self.assertIs(provider.bitbucket_client, bitbucket_client)
        # PR should be set from the mock get_pull_request return value
        self.assertEqual(provider.pr.title, "Test PR")
