import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.utils.chunk_localizer')
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
    def test_create_chunks_get_parser_attribute_error(self):
        """Ensure that when get_parser raises AttributeError we fall back to raw string chunking."""
        text = 'line1\nline2\nline3'
        # Patch get_parser to raise AttributeError to trigger the except branch
        with unittest.mock.patch('openhands.utils.chunk_localizer.get_parser', side_effect=AttributeError):
            chunks = create_chunks(text, size=2, language='nonexistent_language')

        # Should fall back to raw string chunking behavior
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, 'line1\nline2')
        self.assertEqual(chunks[0].line_range, (1, 2))
        self.assertEqual(chunks[1].text, 'line3')
        self.assertEqual(chunks[1].line_range, (3, 3))
