import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.agent')
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
    @patch('langchain_openai.OpenAIEmbeddings')
    def test_case_XX(self, mock_embeddings):
        """Ensure that providing a valid mcp_strategy returns it unchanged."""
        # Create researcher with an explicit, valid mcp_strategy
        researcher = GPTResearcher(query="test query", mcp_strategy="deep")
        # The resolved strategy should be exactly what was passed in
        self.assertEqual(researcher.mcp_strategy, "deep")
