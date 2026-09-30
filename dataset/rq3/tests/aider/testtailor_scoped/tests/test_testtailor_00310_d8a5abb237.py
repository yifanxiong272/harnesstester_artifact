import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.models')
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
        """sanity_check_model should warn when keys_in_environment is False and missing_keys is empty"""
        # Create a mock IO object
        io = MagicMock()

        # Create a mock model with no missing_keys and keys_in_environment=False
        model = MagicMock()
        model.missing_keys = []  # falsy -> skip first if
        model.keys_in_environment = False  # triggers the elif branch we want
        model.name = "custom-model"
        model.info = {"context_window": 1024}  # truthy to avoid the later info-warning branch

        # Patch check_for_dependencies to avoid side effects
        with patch("aider.models.check_for_dependencies") as mock_check:
            show = sanity_check_model(io, model)

        # The function should return True (show warnings)
        self.assertTrue(show)

        # Ensure a warning about unknown environment variables was emitted
        found = False
        for call in io.tool_warning.call_args_list:
            args = call[0]
            if args and "Unknown which environment variables are required." in args[0]:
                found = True
                break

        self.assertTrue(found, "Expected warning about unknown environment variables was not emitted")
