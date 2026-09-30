import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.chat')
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
        """ChatOpenAI.name should return str(self.model)."""
        # When model is a plain string, name should be the same string.
        model_value = "o4-mini"
        chat = ChatOpenAI(model=model_value)
        self.assertEqual(chat.name, model_value)

        # Also verify that non-string model objects are stringified via __str__.
        class DummyModel:
            def __str__(self):
                return "dummy-model"

        chat2 = ChatOpenAI(model=DummyModel())
        self.assertEqual(chat2.name, "dummy-model")
