import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.base_coder')
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
    def test_create_without_main_model_uses_default(self):
        """When no main_model and no from_coder are provided, create() should
        instantiate the default model (models.DEFAULT_MODEL_NAME) and set
        the coder's edit_format from that model.
        """
        io = InputOutput(pretty=False, fancy_input=False, yes=True)

        # Call create without main_model and without from_coder
        coder = Coder.create(io=io)

        # Ensure a main_model was set to the default
        self.assertIsNotNone(coder.main_model)
        self.assertEqual(coder.main_model.name, models.DEFAULT_MODEL_NAME)

        # When edit_format is None and from_coder is not provided, coder.edit_format
        # should default to main_model.edit_format
        self.assertEqual(coder.edit_format, coder.main_model.edit_format)

        # The provided io should be used
        self.assertIs(coder.io, io)
