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
        pr_url = "https://git.onpreminstance.com/projects/AAA/repos/my-repo/pull-requests/1"

        settings_dict = {
            "BITBUCKET_SERVER.BEARER_TOKEN": "FAKE_TOKEN",
            "BITBUCKET_SERVER.USERNAME": None,
            "BITBUCKET_SERVER.PASSWORD": None,
        }

        with patch("pr_agent.git_providers.bitbucket_server_provider.get_settings") as mock_get_settings, \
             patch("pr_agent.git_providers.bitbucket_server_provider.Bitbucket", create=True) as MockBitbucket:

            mock_get_settings.return_value = settings_dict

            mock_instance = MagicMock()
            # Bitbucket.get(...) should return a dict with 'version' so __init__ can parse it
            mock_instance.get.return_value = {"version": "8.1"}
            # ensure set_pr() won't fail when called during __init__
            mock_instance.get_pull_request.return_value = {
                "toRef": {"latestCommit": "HEAD"},
                "fromRef": {"latestCommit": "BASE"},
                "version": 1,
                "reviewers": []
            }

            MockBitbucket.return_value = mock_instance

            provider = BitbucketServerProvider(pr_url=pr_url)

            # Bitbucket should be instantiated with the parsed server URL and the bearer token
            MockBitbucket.assert_called_once()
            called_kwargs = MockBitbucket.call_args.kwargs
            self.assertEqual(called_kwargs.get("url"), "https://git.onpreminstance.com")
            self.assertEqual(called_kwargs.get("token"), "FAKE_TOKEN")

            # provider should have the mocked instance as its client and bearer token set
            self.assertIs(provider.bitbucket_client, mock_instance)
            self.assertEqual(provider.bearer_token, "FAKE_TOKEN")
            # bitbucket_api_version should be set from the mocked get() return value
            self.assertEqual(str(provider.bitbucket_api_version), "8.1")
