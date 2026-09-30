import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skills.utils')
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
    def test_case_00(self):
        """Return an empty pydantic model when parameters is falsy (empty list)."""
        model_name = "EmptyModel"
        model = convert_parameters_to_pydantic([], model_name=model_name)

        # The function should return a class (type) that is a subclass of BaseModel
        self.assertIsInstance(model, type)
        self.assertTrue(issubclass(model, BaseModel))

        # The model should have the requested name and no fields
        self.assertEqual(model.__name__, model_name)
        self.assertEqual(getattr(model, "__fields__", {}), {})

        # We should be able to instantiate it and get an empty dict representation
        instance = model()
        self.assertIsInstance(instance, BaseModel)
        self.assertEqual(instance.dict(), {})
