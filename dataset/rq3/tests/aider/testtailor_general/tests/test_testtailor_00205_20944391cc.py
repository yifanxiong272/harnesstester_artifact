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
    def test_case_XX(self):
        """Ensure tokenize returns immediately when already tokenized (early return branch)."""
        root = ""
        rel_fnames = ["some_file.txt"]
        addable_rel_fnames = []
        commands = None

        autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")

        # Put a sentinel value in words and mark as already tokenized.
        autocompleter.words.add(("sentinel", "sentinel"))
        before_words = set(autocompleter.words)
        autocompleter.tokenized = True

        # Patch open to fail if called — tokenize should return before any file ops.
        with patch("builtins.open", side_effect=AssertionError("open should not be called")):
            result = autocompleter.tokenize()

        # tokenize has no return value (None) and should not have modified words.
        self.assertIsNone(result)
        self.assertEqual(autocompleter.words, before_words)
