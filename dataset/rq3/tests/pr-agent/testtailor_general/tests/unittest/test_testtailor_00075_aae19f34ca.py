import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_provider')
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
        """When diff.new.path is falsy, _gef_filename should return diff.old.path."""
        diff = MagicMock()
        # simulate a diff where the new path is empty/false and old.path holds the real filename
        diff.new.path = ''
        diff.old.path = 'path/to/old_file.txt'

        result = _gef_filename(diff)

        self.assertEqual(result, 'path/to/old_file.txt')
