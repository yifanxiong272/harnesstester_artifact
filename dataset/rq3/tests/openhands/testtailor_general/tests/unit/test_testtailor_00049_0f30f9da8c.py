import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.browsing_agent.browsing_agent')
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
        """Verify get_error_prefix returns the exact formatted message including the last action."""
        last_action = 'click button "Submit" at (10,20)'
        expected = (
            'IMPORTANT! Last action is incorrect:\n'
            f'{last_action}\n'
            'Think again with the current observation of the page.\n'
        )
        result = get_error_prefix(last_action)
        self.assertEqual(result, expected)
