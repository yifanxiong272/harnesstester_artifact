import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.azure.chat')
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
        """Ensure get_client returns the already-set client without creating a new one."""
        llm = ChatAzureOpenAI(
            model='gpt-4',
            api_key='test-key',
            azure_endpoint='https://test.openai.azure.com',
        )

        sentinel_client = object()
        llm.client = sentinel_client

        returned = llm.get_client()

        # get_client should return the same object we set and not replace it
        self.assertIs(returned, sentinel_client)
        self.assertIs(llm.client, sentinel_client)
