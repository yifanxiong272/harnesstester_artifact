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
        """Ensure cached command completions (self.command_completions[cmd]) are used."""
        # Prepare a mocked commands object
        commands = MagicMock()
        commands.get_commands.return_value = ["/add", "/help"]
        # matching_commands should indicate that "/add" matches uniquely
        commands.matching_commands.return_value = (["/add"], "", "")
        # No raw completer for this command
        commands.get_raw_completions.return_value = None
        # Provide a get_completions implementation but it should NOT be called because we will use cache
        commands.get_completions = MagicMock(return_value=["should-not-be-used"])

        # Create AutoCompleter with the mocked commands
        autocompleter = AutoCompleter(
            root="",
            rel_fnames=[],
            addable_rel_fnames=[],
            commands=commands,
            encoding="utf-8",
        )

        # Prime the cache for command "/add"
        cached_candidates = ["file1.txt", "file2.txt", "other.txt"]
        autocompleter.command_completions["/add"] = cached_candidates

        # Prepare inputs to request completions for the second argument partial "f"
        text = "/add f"
        # Document and CompleteEvent are not required for this path (no raw completer),
        # so pass None to avoid relying on imports in the test harness.
        document = None
        complete_event = None
        words = text.split()

        # Call the method under test
        completions = list(
            autocompleter.get_command_completions(document, complete_event, text, words)
        )

        # Extract completion texts
        completion_texts = [c.text for c in completions]

        # We expect only cached entries containing "f" (case-insensitive)
        expected = {"file1.txt", "file2.txt"}
        self.assertEqual(set(completion_texts), expected)

        # Ensure commands.get_completions was not invoked (cache path taken)
        commands.get_completions.assert_not_called()
