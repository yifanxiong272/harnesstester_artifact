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
        """Ensure raw completer returned by commands.get_raw_completions is invoked."""
        # Prepare a commands mock that reports a single matching command and provides a raw completer
        commands = MagicMock()
        cmd_name = "/custom"
        commands.get_commands.return_value = [cmd_name]
        # matching_commands should return a list containing the command so the code accepts it
        commands.matching_commands.side_effect = lambda inp: ([cmd_name], None, None)

        # Define a raw completer that yields simple objects with a 'text' attribute
        def raw_completer(document, complete_event):
            class Item:
                def __init__(self, text):
                    self.text = text

            yield Item("raw_one")
            yield Item("raw_two")

        commands.get_raw_completions.side_effect = lambda c: raw_completer if c == cmd_name else None

        # Create AutoCompleter with the mocked commands
        autocompleter = AutoCompleter(
            root="", rel_fnames=[], addable_rel_fnames=[], commands=commands, encoding="utf-8"
        )

        # Prepare input that has a command and an argument (so we reach the raw_completer branch)
        text = "/custom arg"
        # Use simple stand-ins for document and complete_event (raw_completer does not use them)
        document = object()
        complete_event = object()
        words = text.split()

        completions = list(
            autocompleter.get_command_completions(document, complete_event, text, words)
        )
        completion_texts = [getattr(c, "text", None) for c in completions]

        self.assertEqual(completion_texts, ["raw_one", "raw_two"])
