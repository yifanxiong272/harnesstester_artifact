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
    def test_case_XX(self):
        """Create a parameter schema and ensure convert_parameters_to_pydantic builds a model with the expected field."""
        # Minimal stand-in for the ParameterSchema used by the function under test
        class Param:
            def __init__(self, name, type, required=None, description=None):
                self.name = name
                self.type = type
                self.required = required
                self.description = description

        # Create a single optional numeric parameter with a description
        param = Param(name='age', type='number', required=False, description='Age in years')

        # Call the function under test
        model = convert_parameters_to_pydantic([param], model_name='TestModel')

        # Basic checks on the returned model
        self.assertTrue(issubclass(model, BaseModel))
        self.assertEqual(model.__name__, 'TestModel')

        # Instantiate without the optional field; should succeed and the field should be None
        inst = model()
        self.assertTrue(hasattr(inst, 'age'))
        self.assertIsNone(inst.age)

        # Instantiate with a value and ensure it is parsed to float
        inst2 = model(age=30)
        # pydantic should coerce numeric to float
        self.assertIsInstance(inst2.age, float)
        self.assertEqual(inst2.age, 30.0)
