import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.gitea_provider')
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
    @patch('pr_agent.git_providers.gitea_provider.get_logger')
    def test_case_XX(self, mock_get_logger):
        """Ensure providing no URL logs an error and raises ValueError."""
        # Prepare a mock logger to capture error calls
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from pr_agent.git_providers.gitea_provider import GiteaProvider

        with self.assertRaises(ValueError) as cm:
            GiteaProvider(None)

        # Verify the exception message
        self.assertEqual(str(cm.exception), "PR URL not provided.")

        # Verify logger.error was called with the expected message
        mock_logger.error.assert_called_with("PR URL not provided.")
