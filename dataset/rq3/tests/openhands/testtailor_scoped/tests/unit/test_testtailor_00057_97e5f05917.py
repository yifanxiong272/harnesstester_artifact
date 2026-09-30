import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.azure_devops.service.prs')
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
        """Return original comment when length is equal to max_length (<= branch)."""
        # Create a comment exactly at the default max length (1000)
        comment = "x" * 1000

        # Call the mixin method directly; it does not use `self`
        result = AzureDevOpsPRsMixin._truncate_comment(None, comment)

        # Should return the original comment unchanged and not append ellipsis
        self.assertEqual(result, comment)
        self.assertFalse(result.endswith("..."))
