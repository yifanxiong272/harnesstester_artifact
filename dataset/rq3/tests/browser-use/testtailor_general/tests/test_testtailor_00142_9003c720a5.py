import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.base')
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
        """Tests that the model_name property returns the underlying model attribute (legacy support)."""
        class DummyModel(BaseChatModel):
            def __init__(self, model: str):
                self.model = model

        dm = DummyModel("test-model-123")
        self.assertEqual(dm.model_name, "test-model-123")

        # changing the underlying attribute should be reflected by the property
        dm.model = "updated-model-456"
        self.assertEqual(dm.model_name, "updated-model-456")
