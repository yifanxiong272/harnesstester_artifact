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
        """Ensure BitbucketServerProvider parses server URL and constructs Bitbucket client when no client is provided."""
        pr_url = "https://git.onpreminstance.com/projects/AAA/repos/my-repo/pull-requests/1"

        settings_dict = {
            "BITBUCKET_SERVER.BEARER_TOKEN": None,
            "BITBUCKET_SERVER.USERNAME": "user",
            "BITBUCKET_SERVER.PASSWORD": "pass",
        }

        # Patch the module that contains BitbucketServerProvider (correct module name)
        with patch('pr_agent.git_providers.bitbucket_server_provider.get_settings') as mock_get_settings, \
             patch('pr_agent.git_providers.bitbucket_server_provider.Bitbucket', create=True) as mock_bb, \
             patch('pr_agent.git_providers.bitbucket_server_provider.BitbucketServerProvider.set_pr', return_value=None) as mock_set_pr:

            # Configure get_settings().get(...) to return values from our dict
            mock_get_settings.return_value.get.side_effect = lambda key, default=None: settings_dict.get(key, default)

            # Configure the mocked Bitbucket instance to return an API version for the application-properties call
            mock_instance = mock_bb.return_value
            mock_instance.get.return_value = {"version": "7.0"}

            provider = BitbucketServerProvider(pr_url)

            # _parse_bitbucket_server should result in the base server url (no trailing path)
            assert provider.bitbucket_server_url == "https://git.onpreminstance.com"

            # Bitbucket constructor should have been called with username/password (since no bearer token)
            mock_bb.assert_called_once_with(url="https://git.onpreminstance.com", username="user", password="pass")

            # Ensure the API version was parsed and set
            assert provider.bitbucket_api_version is not None

            # Ensure pr_url was stored
            assert provider.pr_url == pr_url

            # Ensure set_pr was invoked during initialization
            mock_set_pr.assert_called_once()
