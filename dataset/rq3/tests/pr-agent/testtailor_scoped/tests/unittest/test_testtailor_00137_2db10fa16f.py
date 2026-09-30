import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.gitlab_provider')
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
        """Verify that when GITLAB.AUTH_TYPE is 'private_token' the Gitlab client is created with private_token."""
        # Prepare setting values to force the private_token branch
        settings_map = {
            "GITLAB.URL": "https://gitlab.example.com",
            "GITLAB.PERSONAL_ACCESS_TOKEN": "token123",
            "GITLAB.AUTH_TYPE": "private_token",
            "GITLAB.SSL_VERIFY": False,
        }

        with patch('pr_agent.git_providers.gitlab_provider.gitlab.Gitlab') as mock_gitlab_cls, \
             patch('pr_agent.git_providers.gitlab_provider.get_settings') as mock_get_settings, \
             patch('pr_agent.git_providers.gitlab_provider.GitLabProvider._set_merge_request') as mock_set_mr:

            # Configure get_settings().get(...) to return values from our map
            mock_get_settings.return_value.get.side_effect = lambda key, default=None: settings_map.get(key, default)

            # Ensure _set_merge_request does nothing (avoid network calls / further initialization)
            mock_set_mr.return_value = None

            # Instantiate provider; this should call the private_token branch
            from pr_agent.git_providers.gitlab_provider import GitLabProvider
            provider = GitLabProvider("https://gitlab.example.com/group/repo/-/merge_requests/42", incremental=True)

            # Assert Gitlab was constructed with private_token (not oauth_token) and correct args
            mock_gitlab_cls.assert_called_once_with(
                url="https://gitlab.example.com",
                private_token="token123",
                ssl_verify=False
            )

            # Basic attribute checks to ensure init proceeded
            self.assertEqual(provider.gitlab_url, "https://gitlab.example.com")
            self.assertTrue(provider.incremental)
            # provider.gl should be the return value of the mocked Gitlab class
            self.assertIs(provider.gl, mock_gitlab_cls.return_value)
