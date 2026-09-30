import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.azuredevops_provider')
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
        """When AZURE_DEVOPS_AVAILABLE is False, __init__ should raise ImportError."""
        with patch("pr_agent.git_providers.azuredevops_provider.AZURE_DEVOPS_AVAILABLE", False):
            with self.assertRaises(ImportError) as cm:
                AzureDevopsProvider()
            self.assertIn(
                "Azure DevOps provider is not available. Please install the required dependencies.",
                str(cm.exception),
            )
