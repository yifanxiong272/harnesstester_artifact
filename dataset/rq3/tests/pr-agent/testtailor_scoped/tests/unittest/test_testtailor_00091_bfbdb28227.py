import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_code_suggestions')
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
        """PRCodeSuggestions.run returns None and exits early when git_provider.get_files() is empty."""
        # create a minimal PRCodeSuggestions instance without running __init__
        pr_obj = PRCodeSuggestions.__new__(PRCodeSuggestions)

        # mock git_provider with get_files returning an empty list
        mock_git_provider = MagicMock()
        mock_git_provider.get_files.return_value = []

        # attach minimal required attributes
        pr_obj.git_provider = mock_git_provider
        pr_obj.pr_url = "http://example.com/pr/1"

        # call the async run method and assert it returns None (early exit)
        result = asyncio.run(pr_obj.run())
        self.assertIsNone(result)
        mock_git_provider.get_files.assert_called_once()
