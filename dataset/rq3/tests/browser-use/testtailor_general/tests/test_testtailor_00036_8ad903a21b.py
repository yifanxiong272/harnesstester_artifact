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
		"""Filenames with invalid characters but a supported extension should return the generic invalid-filename message."""
		file_name = 'invalid@name.md'
		supported_extensions = ['md', 'txt']

		msg = _build_filename_error_message(file_name, supported_extensions)

		expected = (
			"Error: Invalid filename 'invalid@name.md'. "
			"Filenames must contain only letters, numbers, underscores, hyphens, dots, parentheses, and spaces. "
			"Supported extensions: .md, .txt."
		)

		self.assertEqual(msg, expected)
