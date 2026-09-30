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
        """Truncate when comment longer than max_length appends ellipsis."""
        long_comment = 'a' * 15
        max_length = 10

        # Call the unbound method; it does not use self, so None is fine
        result = AzureDevOpsPRsMixin._truncate_comment(None, long_comment, max_length)

        expected = 'a' * max_length + '...'
        self.assertEqual(result, expected)
        self.assertEqual(len(result), max_length + 3)
