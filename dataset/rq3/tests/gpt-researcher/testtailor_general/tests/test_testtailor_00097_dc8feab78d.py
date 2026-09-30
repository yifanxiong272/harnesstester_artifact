import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.utils.utils')
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
        """Sanitize filenames by replacing invalid Windows path characters with underscores."""
        # Example from the function docstring
        original = 'invalid:file/name*example?.txt'
        expected = 'invalid_file_name_example_.txt'
        self.assertEqual(sanitize_filename(original), expected)

        # All invalid characters together should become underscores (9 invalid chars)
        original_all = '<>:"/\\|?*'
        expected_all = '_' * 9
        self.assertEqual(sanitize_filename(original_all), expected_all)

        # A valid filename should remain unchanged
        valid = 'valid_filename.txt'
        self.assertEqual(sanitize_filename(valid), valid)
