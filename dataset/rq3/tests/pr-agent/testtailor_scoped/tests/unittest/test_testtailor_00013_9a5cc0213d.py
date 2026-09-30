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
    def test_case_01(self):
        """Should raise ValueError when GITLAB.URL is not set in the config"""
        from unittest.mock import patch, MagicMock
        from pr_agent.git_providers.gitlab_provider import GitLabProvider

        # Make get_settings().get(...) return None for the GITLAB.URL (and generally)
        mock_settings = MagicMock()
        mock_settings.get.return_value = None

        with patch('pr_agent.git_providers.gitlab_provider.get_settings', return_value=mock_settings):
            with self.assertRaisesRegex(ValueError, "GitLab URL is not set in the config file"):
                GitLabProvider(merge_request_url=None)
