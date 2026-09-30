import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.chat')
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
        """Verify that ChatGroq.name returns str(self.model)."""
        # model as a plain string
        cg = ChatGroq(model="groq-mini")
        self.assertEqual(cg.name, "groq-mini")

        # model as an object implementing __str__
        class DummyModel:
            def __str__(self):
                return "dummy-model"

        cg_obj = ChatGroq(model=DummyModel())
        self.assertEqual(cg_obj.name, "dummy-model")
