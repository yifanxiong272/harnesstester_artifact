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
    def test_return_on_space_or_short_words(self):
        """Ensure get_command_completions returns immediately when words length <= 1
        or the text ends with a space (covers the `return` branch)."""
        # Create an AutoCompleter with no commands so command_names is not set.
        autocompleter = AutoCompleter(root="", rel_fnames=[], addable_rel_fnames=[], commands=None, encoding="utf-8")

        # Case: single word with trailing space -> should return immediately (no completions)
        text = "/add "
        words = text.strip().split()  # ['/add']
        # Pass None for document and complete_event since the early return avoids using them.
        completions = list(autocompleter.get_command_completions(None, None, text, words))
        self.assertEqual(completions, [])
