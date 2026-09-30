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
    def test_publish_code_suggestions_with_invalid_start(self):
        """If relevant_lines_start is -1 the provider should skip that suggestion and return True."""
        provider = object.__new__(AzureDevopsProvider)
        # Do not call __init__; we only need to exercise the branch where relevant_lines_start is invalid.
        suggestions = [
            {
                "body": "Suggested change",
                "relevant_file": "some/file.py",
                "relevant_lines_start": -1,  # triggers the warning branch
                "relevant_lines_end": 10,
            }
        ]
        result = provider.publish_code_suggestions(suggestions)
        self.assertTrue(result)
