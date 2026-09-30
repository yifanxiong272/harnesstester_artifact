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
        """When no gmail_service is provided but access_token is given, register_gmail_actions should
        instantiate GmailService with the provided access token and assign it to the module-level _gmail_service.
        """
        # Prepare
        tools = Tools()

        # Access the function and its globals
        func = register_gmail_actions
        g = func.__globals__

        # Save originals to restore later
        orig_GmailService = g.get('GmailService')
        orig__gmail_service = g.get('_gmail_service', None)

        # Create a fake GmailService to capture the initialization argument
        class FakeGmailService:
            def __init__(self, access_token: str | None = None):
                self.access_token = access_token

        try:
            # Patch the GmailService in the function's globals
            g['GmailService'] = FakeGmailService

            # Call with access_token and no gmail_service to hit the target branch
            returned_tools = func(tools=tools, gmail_service=None, access_token='token-XYZ')

            # Ensure the function returns the same tools object
            self.assertIs(returned_tools, tools)

            # Verify that the module-level _gmail_service was set to our FakeGmailService instance
            module_service = g.get('_gmail_service')
            self.assertIsNotNone(module_service, "_gmail_service should be set after calling register_gmail_actions")
            self.assertIsInstance(module_service, FakeGmailService)
            self.assertEqual(module_service.access_token, 'token-XYZ')
        finally:
            # Restore originals to avoid side effects on other tests
            if orig_GmailService is not None:
                g['GmailService'] = orig_GmailService
            else:
                g.pop('GmailService', None)
            if orig__gmail_service is not None:
                g['_gmail_service'] = orig__gmail_service
            else:
                g.pop('_gmail_service', None)
