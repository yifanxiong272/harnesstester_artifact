import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.filesystem.file_system')
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
        """Trigger the 'Invalid filename' error message path for a supported extension but invalid name."""
        # Filename has an invalid character (@) but a supported extension 'md'
        file_name = 'bad@name.md'
        supported_extensions = ['md', 'txt']

        # Import the target module using __import__ to avoid top-level import statements
        module = __import__('browser_use.filesystem.file_system', fromlist=['_build_filename_error_message'])

        # Call the helper directly
        result = module._build_filename_error_message(file_name, supported_extensions)

        # Assert the message indicates an invalid filename and includes the basename
        self.assertTrue(result.startswith("Error: Invalid filename 'bad@name.md'. "))

        # Assert it mentions the allowed character set text
        self.assertIn(
            'Filenames must contain only letters, numbers, underscores, hyphens, dots, parentheses, and spaces',
            result,
        )

        # Assert supported extensions are listed in the message
        self.assertIn('.md', result)
        self.assertIn('.txt', result)
