import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.parsing')
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
    def test_call_base_raises_not_implemented(self):
        """Ensure calling the base AbstractParseFunction.__call__ raises NotImplementedError."""
        class DummyParse(AbstractParseFunction):
            # override to allow instantiation but delegate to base implementation
            def __call__(self, model_response, commands, strict=False):
                return super().__call__(model_response, commands, strict)

        parser = DummyParse()
        with self.assertRaises(NotImplementedError):
            parser("some response", [])
