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
        """Ensure get_command_completions returns nothing when commands.get_completions returns None."""
        # Mock commands
        commands = MagicMock()
        commands.get_commands.return_value = ["/help", "/drop"]
        # matching_commands should return a single match for '/drop' so the completer proceeds
        commands.matching_commands.side_effect = lambda inp: (["/drop"] if inp == "/drop" else [], None, None)
        commands.get_raw_completions.return_value = None
        # Simulate get_completions returning None for "/drop"
        commands.get_completions.side_effect = lambda cmd: None if cmd == "/drop" else ["irrelevant"]

        # Create AutoCompleter with the mocked commands
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=[],
            addable_rel_fnames=[],
            commands=commands,
            encoding="utf-8",
        )

        # Prepare input that will select the "/drop" command and have a partial arg
        text = "/drop x"
        words = text.split()  # ['/drop', 'x']

        # Call get_command_completions with document and complete_event as None
        completions = list(
            autocompleter.get_command_completions(
                None,
                None,
                text,
                words,
            )
        )

        # Expect no completions because get_completions returned None
        self.assertEqual(completions, [])

        # Ensure the result was cached as None on the completer
        self.assertIn("/drop", autocompleter.command_completions)
        self.assertIsNone(autocompleter.command_completions["/drop"])
