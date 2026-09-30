import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.browsing_agent.response_parser')
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
        """Ensure parse handles string response input path (isinstance(response, str))."""
        parser = BrowsingResponseParser()
        action_str = "click('81')```"
        action = parser.parse(action_str)
        self.assertIsInstance(action, BrowseInteractiveAction)
        self.assertEqual(action.browser_actions, "click('81')")
        self.assertEqual(action.thought, '')
        self.assertEqual(action.browsergym_send_msg_to_user, '')
        self.assertFalse(action.return_axtree)
