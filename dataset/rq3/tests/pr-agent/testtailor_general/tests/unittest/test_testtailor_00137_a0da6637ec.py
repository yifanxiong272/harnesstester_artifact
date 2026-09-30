import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_provider')
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
        """Test BitbucketProvider __init__ sets up session headers and auth types (bearer and basic)."""
        pr_url = "https://bitbucket.org/WORKSPACE/REPO/pull-requests/1"

        # Common PR mock that provides the __data expected by __init__
        pr_mock = MagicMock()
        pr_mock._BitbucketBase__data = {
            "links": {
                "comments": {"href": "https://api.bitbucket.org/2.0/repositories/WORKSPACE/REPO/pullrequests/1/comments"},
                "self": {"href": "https://api.bitbucket.org/2.0/repositories/WORKSPACE/REPO/pullrequests/1"}
            }
        }

        # Build cloud client structure: cloud().workspaces.get(...).repositories.get(...).pullrequests.get(...) -> pr_mock
        cloud_client = MagicMock()
        workspace_mock = MagicMock()
        repo_mock = MagicMock()
        pullrequests_collection = MagicMock()
        pullrequests_collection.get.return_value = pr_mock
        repo_mock.pullrequests = pullrequests_collection
        workspace_mock.repositories.get.return_value = repo_mock
        cloud_client.workspaces.get.return_value = workspace_mock

        # --------------------
        # Bearer auth scenario
        # --------------------
        settings_map_bearer = {"BITBUCKET.AUTH_TYPE": "bearer", "BITBUCKET.BEARER_TOKEN": "TOKEN123"}
        settings_mock_bearer = MagicMock()
        settings_mock_bearer.get.side_effect = lambda key, default=None: settings_map_bearer.get(key, default)

        context_mock = MagicMock()
        context_mock.get.return_value = None  # force using settings BEARER_TOKEN

        session_mock = MagicMock()
        session_mock.headers = {}

        with patch("pr_agent.git_providers.bitbucket_provider.get_settings", return_value=settings_mock_bearer), \
             patch("pr_agent.git_providers.bitbucket_provider.context", context_mock), \
             patch("pr_agent.git_providers.bitbucket_provider.requests.Session", return_value=session_mock), \
             patch("pr_agent.git_providers.bitbucket_provider.Cloud", return_value=cloud_client):

            provider = BitbucketProvider(pr_url=pr_url, incremental=False)

            # Assertions for bearer flow
            self.assertEqual(provider.auth_type, "bearer")
            self.assertEqual(provider.bearer_token, "TOKEN123")
            self.assertEqual(provider.headers["Content-Type"], "application/json")
            self.assertEqual(provider.headers["Authorization"], "Bearer TOKEN123")
            # bitbucket_client should be the cloud_client we provided
            self.assertIs(provider.bitbucket_client, cloud_client)
            # bitbucket_comment_api_url and pull_request_api_url should be set from pr_mock data
            self.assertEqual(provider.bitbucket_comment_api_url, pr_mock._BitbucketBase__data["links"]["comments"]["href"])
            self.assertEqual(provider.bitbucket_pull_request_api_url, pr_mock._BitbucketBase__data["links"]["self"]["href"])

        # --------------------
        # Basic auth scenario
        # --------------------
        settings_map_basic = {"BITBUCKET.AUTH_TYPE": "basic", "BITBUCKET.BASIC_TOKEN": "BASIC123"}
        settings_mock_basic = MagicMock()
        settings_mock_basic.get.side_effect = lambda key, default=None: settings_map_basic.get(key, default)

        session_mock2 = MagicMock()
        session_mock2.headers = {}

        # Reuse cloud_client but ensure workspace/repo/pullrequests chain returns our pr_mock
        with patch("pr_agent.git_providers.bitbucket_provider.get_settings", return_value=settings_mock_basic), \
             patch("pr_agent.git_providers.bitbucket_provider.context", context_mock), \
             patch("pr_agent.git_providers.bitbucket_provider.requests.Session", return_value=session_mock2), \
             patch("pr_agent.git_providers.bitbucket_provider.Cloud", return_value=cloud_client):

            provider_basic = BitbucketProvider(pr_url=pr_url, incremental=False)

            # Assertions for basic flow
            self.assertEqual(provider_basic.auth_type, "basic")
            self.assertEqual(provider_basic.basic_token, "BASIC123")
            self.assertEqual(provider_basic.headers["Content-Type"], "application/json")
            self.assertEqual(provider_basic.headers["Authorization"], "Basic BASIC123")
            self.assertIs(provider_basic.bitbucket_client, cloud_client)
            self.assertEqual(provider_basic.bitbucket_comment_api_url, pr_mock._BitbucketBase__data["links"]["comments"]["href"])
            self.assertEqual(provider_basic.bitbucket_pull_request_api_url, pr_mock._BitbucketBase__data["links"]["self"]["href"])
