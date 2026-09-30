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
        """Ensure deprecated 'optimized' mcp_strategy maps to 'fast' with backwards-compat handling."""
        # Construct researcher using the deprecated strategy name
        researcher = GPTResearcher(query="dummy query", mcp_strategy="optimized")

        # The deprecated name should be normalized to "fast"
        self.assertEqual(researcher.mcp_strategy, "fast")
