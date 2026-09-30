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
    def test_case_XX(self):
        """Memory.get_embeddings should return the underlying embeddings instance."""
        with patch('langchain_openai.OpenAIEmbeddings') as mock_openai_emb:
            sentinel = object()
            mock_openai_emb.return_value = sentinel

            # Construct Memory with provider that uses OpenAIEmbeddings
            mem = Memory("openai", "text-embedding-3-small")

            # get_embeddings should return the exact object created by OpenAIEmbeddings
            embeddings = mem.get_embeddings()
            self.assertIs(embeddings, sentinel)

            # Ensure the OpenAIEmbeddings constructor was called with the model arg
            mock_openai_emb.assert_called_once_with(model="text-embedding-3-small")
