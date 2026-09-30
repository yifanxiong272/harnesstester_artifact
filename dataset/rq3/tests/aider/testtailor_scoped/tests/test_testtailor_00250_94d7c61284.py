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
        """Ensure get_command_completions returns nothing when words length <= 1 or trailing space."""
        # Create AutoCompleter without a commands object since we only exercise the early return path.
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=[],
            addable_rel_fnames=[],
            commands=None,
            encoding="utf-8",
        )

        class DummyDoc:
            def __init__(self, text):
                self.text_before_cursor = text

        # Case 1: Trailing space -> should return immediately (no completions)
        text1 = "/add "
        doc1 = DummyDoc(text1)
        words1 = text1.split()  # ['/add']
        completions1 = list(
            autocompleter.get_command_completions(doc1, None, text1, words1)
        )
        self.assertEqual(completions1, [])

        # Case 2: Empty words (len(words) <= 1) -> should return immediately
        text2 = ""
        doc2 = DummyDoc(text2)
        words2 = text2.split()  # []
        completions2 = list(
            autocompleter.get_command_completions(doc2, None, text2, words2)
        )
        self.assertEqual(completions2, [])
