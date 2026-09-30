import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.integrations.gmail.actions')
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
        """Verify that providing a gmail_service sets the module-level _gmail_service to that instance."""
        # Create a Tools instance to register actions on
        tools = Tools()

        # Create a sentinel object to act as the gmail_service
        sentinel = object()

        # Call the function under test with the gmail_service provided
        returned = register_gmail_actions(tools, gmail_service=sentinel)

        # The function should return the same Tools instance
        self.assertIs(returned, tools)

        # The module-level _gmail_service used by register_gmail_actions should be set to our sentinel.
        # Access the function's globals to find the module-level variable it assigns.
        module_globals = register_gmail_actions.__globals__
        self.assertIn('_gmail_service', module_globals)
        self.assertIs(module_globals['_gmail_service'], sentinel)
