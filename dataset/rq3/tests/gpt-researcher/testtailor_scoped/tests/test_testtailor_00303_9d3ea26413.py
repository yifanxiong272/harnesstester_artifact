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
        """When headers and cfg provide no retriever(s), get_retrievers should return the default retriever class."""
        headers = {}
        cfg = MagicMock()
        cfg.retrievers = None
        cfg.retriever = None

        retriever_classes = get_retrievers(headers, cfg)

        self.assertIsInstance(retriever_classes, list)
        self.assertEqual(len(retriever_classes), 1)
        self.assertIs(retriever_classes[0], get_default_retriever())
