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
        """Should raise ValueError for unsupported GITLAB.AUTH_TYPE in configuration."""
        # Prepare settings to return an invalid auth type
        with patch('pr_agent.git_providers.gitlab_provider.get_settings') as mock_get_settings:
            mock_get_settings.return_value.get.side_effect = lambda key, default=None: {
                "GITLAB.URL": "https://gitlab.com",
                "GITLAB.PERSONAL_ACCESS_TOKEN": "fake_token",
                "GITLAB.AUTH_TYPE": "unsupported_method"
            }.get(key, default)

            # Attempting to create provider with unsupported auth type should raise ValueError
            with self.assertRaises(ValueError) as cm:
                GitLabProvider("https://gitlab.com/group/repo/-/merge_requests/1")

            self.assertIn("Unsupported GITLAB.AUTH_TYPE", str(cm.exception))
