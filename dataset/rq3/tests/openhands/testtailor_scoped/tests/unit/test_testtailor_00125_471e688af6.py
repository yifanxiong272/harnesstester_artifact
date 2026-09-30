import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.memory')
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
        """Test that InMemoryFileStore.write decodes bytes input using UTF-8."""
        store = InMemoryFileStore()
        path = 'some/path/to/file.txt'
        original_text = 'café — 測試'
        # Provide bytes so isinstance(contents, bytes) is True and decode branch is exercised
        contents_bytes = original_text.encode('utf-8')

        store.write(path, contents_bytes)

        # Verify the file was written and the bytes were decoded to the original string
        self.assertIn(path, store.files)
        self.assertIsInstance(store.files[path], str)
        self.assertEqual(store.files[path], original_text)
