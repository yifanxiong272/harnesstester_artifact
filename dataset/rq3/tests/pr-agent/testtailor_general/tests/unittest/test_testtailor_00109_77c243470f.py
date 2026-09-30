import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.help')
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
    def test_case_01(self):
        """Verify get_general_bot_help_text returns the expected combined help text."""
        result = HelpMessage.get_general_bot_help_text()
        expected = f"> To invoke the PR-Agent, add a comment using one of the following commands:  \n{HelpMessage.get_general_commands_text()} \n"
        self.assertEqual(result, expected)
