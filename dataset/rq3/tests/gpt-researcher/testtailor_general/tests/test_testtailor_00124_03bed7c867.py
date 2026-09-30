import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.memory.embeddings')
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
    def test_get_embeddings_returns_underlying_instance(self, mock_openai_embeddings):
        """Memory.get_embeddings should return the underlying embeddings instance set in __init__."""
        # Arrange: make the patched constructor return a fake embeddings instance
        fake_embeddings = MagicMock(name="FakeEmbeddings")
        mock_openai_embeddings.return_value = fake_embeddings

        # Act: initialize Memory with the "openai" provider and a model name
        mem = Memory("openai", "text-embedding-3-small")

        # Assert: get_embeddings returns the exact object created by the provider constructor
        self.assertIs(mem.get_embeddings(), fake_embeddings)
        # Ensure the provider constructor was invoked exactly once
        self.assertEqual(mock_openai_embeddings.call_count, 1)
