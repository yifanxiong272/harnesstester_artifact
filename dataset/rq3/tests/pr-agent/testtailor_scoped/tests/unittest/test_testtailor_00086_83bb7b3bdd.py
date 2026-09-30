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
        """Verify BitbucketProvider sets up session headers and picks auth_type from settings,
        and that it can initialize PR-related URLs when a PR object is available from Cloud."""
        # Prepare a fake settings object that returns basic auth and a token
        mock_settings = MagicMock()
        def settings_get(key, default=None):
            if key == "BITBUCKET.AUTH_TYPE":
                return "basic"
            if key == "BITBUCKET.BASIC_TOKEN":
                return "basic-tok"
            return default
        mock_settings.get.side_effect = settings_get

        # Prepare a fake PR object with the internal data the __init__ expects
        pr_mock = MagicMock()
        pr_mock._BitbucketBase__data = {
            "links": {
                "comments": {"href": "http://example.com/comments"},
                "self": {"href": "http://example.com/self"}
            }
        }

        # Prepare a fake Cloud client that returns a workspace -> repo -> pullrequests -> pr_mock
        client_mock = MagicMock()
        workspaces_return = MagicMock()
        repos_return = MagicMock()
        pullrequests_return = MagicMock()

        # set up chaining: client.workspaces.get(...).repositories.get(...).pullrequests.get(...) -> pr_mock
        client_mock.workspaces.get.return_value = workspaces_return
        workspaces_return.repositories.get.return_value = repos_return
        repos_return.pullrequests.get.return_value = pr_mock

        # Patch get_settings and Cloud used in the module under test
        with patch("pr_agent.git_providers.bitbucket_provider.get_settings", return_value=mock_settings):
            with patch("pr_agent.git_providers.bitbucket_provider.Cloud", return_value=client_mock):
                # Provide a valid PR URL so __init__ will call set_pr and retrieve the mocked PR
                provider = BitbucketProvider(pr_url="https://bitbucket.org/WORKSPACE/REPO/pull-requests/1")

        # Assertions verifying the initialization behavior
        self.assertEqual(provider.auth_type, "basic")
        self.assertEqual(provider.basic_token, "basic-tok")
        # session headers should include content-type and authorization
        self.assertIn("Content-Type", provider.headers)
        self.assertEqual(provider.headers["Content-Type"], "application/json")
        self.assertIn("Authorization", provider.headers)
        self.assertEqual(provider.headers["Authorization"], "Basic basic-tok")

        # PR related URLs should be taken from the mocked PR object
        self.assertEqual(provider.bitbucket_comment_api_url, "http://example.com/comments")
        self.assertEqual(provider.bitbucket_pull_request_api_url, "http://example.com/self")
