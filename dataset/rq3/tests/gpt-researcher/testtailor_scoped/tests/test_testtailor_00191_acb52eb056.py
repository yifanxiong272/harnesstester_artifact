import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.retriever')
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
        """Ensure cfg.retrievers as a comma string is split, stripped, and mapped to classes."""
        # Arrange: no headers to force using cfg.retrievers branch
        headers = {}
        cfg = MagicMock()
        cfg.retrievers = " google , bing "  # string form with spaces to trigger split() and strip()
        cfg.retriever = None

        # Act
        result = get_retrievers(headers, cfg)

        # Assert: two retriever classes returned and correspond to the expected retrievers
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], get_retriever("google"))
        self.assertIs(result[1], get_retriever("bing"))
