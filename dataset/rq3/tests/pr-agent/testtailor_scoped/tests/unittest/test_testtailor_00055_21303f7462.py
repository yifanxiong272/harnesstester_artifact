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
        """Ensure constructor raises when personal access token is not configured."""
        with patch('pr_agent.git_providers.gitlab_provider.get_settings') as mock_get_settings:
            mock_cfg = MagicMock()
            # GITLAB.URL is present but GITLAB.PERSONAL_ACCESS_TOKEN is missing (None)
            mock_cfg.get.side_effect = lambda key, default=None: {
                "GITLAB.URL": "https://gitlab.com",
                "GITLAB.PERSONAL_ACCESS_TOKEN": None
            }.get(key, default)
            mock_get_settings.return_value = mock_cfg

            with self.assertRaises(ValueError) as cm:
                GitLabProvider("https://gitlab.com/test/repo/-/merge_requests/1")

            self.assertEqual(str(cm.exception), "GitLab personal access token is not set in the config file")
