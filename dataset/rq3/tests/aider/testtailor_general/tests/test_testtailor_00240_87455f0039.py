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
        """Tokenize should handle UnicodeDecodeError from reading files and continue."""
        fname = "bad_encoding.py"
        # Write content encoded as utf-16 so that opening with encoding='utf-8' will raise
        with open(fname, "wb") as f:
            f.write("def bad():\n    return 'åíî'".encode("utf-16"))

        # Create AutoCompleter that will try to read the file using utf-8
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=[fname],
            addable_rel_fnames=[],
            commands=None,
            encoding="utf-8",
        )

        # Before tokenizing, words should contain the rel_fname
        self.assertIn(fname, autocompleter.words)

        # Calling tokenize should not raise despite the UnicodeDecodeError;
        # the exception is caught and the loop should continue.
        autocompleter.tokenize()

        # Since the file couldn't be decoded, no new tokens should have been added.
        self.assertEqual(autocompleter.words, set([fname]))

        # tokenized flag should be set to True even if reading failed
        self.assertTrue(autocompleter.tokenized)

        # Cleanup the created file
        try:
            __import__("os").remove(fname)
        except Exception:
            pass
