import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.cerebras.chat')
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
        """Verify the name property returns the model string."""
        # default instance should expose the default model name
        model_instance = ChatCerebras()
        self.assertIsInstance(model_instance.name, str)
        self.assertEqual(model_instance.name, model_instance.model)

        # custom model provided at construction should be reflected by .name
        custom = ChatCerebras(model='my-custom-model')
        self.assertEqual(custom.name, 'my-custom-model')
