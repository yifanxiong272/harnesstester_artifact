import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.io')
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
    def test_tokenize_returns_if_already_tokenized(self):
        """Ensure tokenize returns immediately when self.tokenized is True."""
        # Create an AutoCompleter with a simple setup
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=["file1.txt"],
            addable_rel_fnames=[],
            commands=None,
            encoding="utf-8",
        )

        # Ensure initial state
        self.assertFalse(autocompleter.tokenized)
        original_words = set(autocompleter.words)

        # Set tokenized to True to force early return path
        autocompleter.tokenized = True

        # Call tokenize; should return immediately and not modify words
        autocompleter.tokenize()

        # Verify no changes occurred
        self.assertTrue(autocompleter.tokenized)
        self.assertEqual(autocompleter.words, original_words)
