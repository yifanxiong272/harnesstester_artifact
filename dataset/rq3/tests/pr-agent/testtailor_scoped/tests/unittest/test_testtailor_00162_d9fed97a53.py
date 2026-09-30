import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.language_handler')
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
        """is_valid_file should return False for known auto-generated filenames (exact matches)."""
        # direct filename
        self.assertFalse(is_valid_file('package-lock.json', bad_extensions=['py']))
        # filename in a path with forward slashes
        self.assertFalse(is_valid_file('some/path/to/yarn.lock', bad_extensions=['py']))
        # filename in a path with backslashes
        self.assertFalse(is_valid_file(r'another\dir\pnpm-lock.yaml', bad_extensions=['py']))
