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
        """Ensure get_command_completions returns nothing when the entered command
        is not among the matching commands and there are multiple matches."""
        # Prepare a commands mock where matching_commands returns multiple matches
        commands = MagicMock()
        commands.get_commands.return_value = ["/add", "/drop"]
        # matching_commands should return multiple matches that do not include the typed cmd
        commands.matching_commands.side_effect = lambda inp: (["/add", "/drop"], None, None)
        commands.get_raw_completions.return_value = None
        commands.get_completions.return_value = None

        # Create AutoCompleter with the mocked commands
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=[],
            addable_rel_fnames=[],
            commands=commands,
            encoding="utf-8",
        )

        # Provide an input where the first token is not in the matches returned
        text = "/unknown arg"
        # document and complete_event are not used on this path, so simple placeholders suffice
        document = None
        complete_event = None
        words = text.strip().split()

        # Collect completions (should be empty because cmd not in matches)
        completions = list(
            autocompleter.get_command_completions(document, complete_event, text, words)
        )

        self.assertEqual(completions, [])
        # Ensure matching_commands was called with the entered command
        commands.matching_commands.assert_called_once_with(words[0])
