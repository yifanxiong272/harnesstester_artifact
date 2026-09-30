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
        """Hit the branch where headers have no retriever(s), cfg.retrievers is falsy, and cfg.retriever is set."""
        # Arrange: headers with no retriever keys
        headers = {}

        # cfg should have no 'retrievers' but should have a single 'retriever'
        cfg = MagicMock()
        cfg.retrievers = None
        cfg.retriever = "tavily"  # a known retriever name from get_retriever's mapping

        # Act
        retriever_classes = get_retrievers(headers, cfg)

        # Assert: should use the cfg.retriever path and return the corresponding retriever class
        self.assertEqual(len(retriever_classes), 1)
        retriever_cls = retriever_classes[0]
        self.assertTrue(hasattr(retriever_cls, "__name__"))
        # Expect the Tavily retriever class to be returned for the 'tavily' key
        self.assertEqual(retriever_cls.__name__, "TavilySearch")
