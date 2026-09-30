import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.model.exp')
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
        # Instantiate ModelTask to exercise its __init__ which calls super().__init__(name=..., description=...)
        name = "example_name"
        description = "example_description"
        task = ModelTask(name=name, description=description)

        # The get_task_information method uses self.name and self.description set via the super().__init__ call
        info = task.get_task_information()
        expected = f"name: {name}\ndescription: {description}\n"
        self.assertEqual(info, expected)
