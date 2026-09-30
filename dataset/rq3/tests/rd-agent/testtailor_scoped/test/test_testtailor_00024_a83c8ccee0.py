import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.factor_coder.factor')
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
        """complete the test case here"""
        # create a FactorTask with explicit values
        vars_dict = {"a": 1, "b": 2}
        ft = FactorTask(
            "my_factor",
            "a short description",
            "x + y",
            variables=vars_dict,
            resource="cpu",
            factor_implementation=True,
        )

        # check that the constructor set the attributes correctly
        self.assertEqual(ft.factor_name, "my_factor")
        self.assertEqual(ft.factor_formulation, "x + y")
        self.assertDictEqual(ft.variables, vars_dict)
        self.assertEqual(ft.factor_resources, "cpu")
        self.assertTrue(ft.factor_implementation)

        # super().__init__ should set description which is exposed via factor_description property
        self.assertEqual(ft.description, "a short description")
        self.assertEqual(ft.factor_description, "a short description")

        # repr should reflect the class name and factor_name
        self.assertEqual(repr(ft), "<FactorTask[my_factor]>")

        # get_task_information should include the key pieces of information
        info = ft.get_task_information()
        self.assertIn("factor_name: my_factor", info)
        self.assertIn("factor_description: a short description", info)
        self.assertIn("factor_formulation: x + y", info)
        self.assertIn(str(vars_dict), info)

        # test from_dict factory method
        d = {
            "factor_name": "f2",
            "factor_description": "desc2",
            "factor_formulation": "a * b",
            "variables": {"x": 10},
            "resource": "gpu",
            "factor_implementation": False,
        }
        ft2 = FactorTask.from_dict(d)
        self.assertEqual(ft2.factor_name, "f2")
        self.assertEqual(ft2.factor_formulation, "a * b")
        self.assertDictEqual(ft2.variables, {"x": 10})
        self.assertEqual(ft2.factor_resources, "gpu")
        self.assertFalse(ft2.factor_implementation)
        self.assertEqual(ft2.factor_description, "desc2")
