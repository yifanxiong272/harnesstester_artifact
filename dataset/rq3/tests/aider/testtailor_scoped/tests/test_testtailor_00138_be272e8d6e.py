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
        """Ensure register_litellm_models wraps underlying exceptions with the expected message."""
        test_fname = "test_model.json"
        # Make os.path.exists return True so the function attempts to read the file,
        # and cause Path.read_text to raise an error to hit the except branch.
        with patch("os.path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=ValueError("boom")):
                with self.assertRaisesRegex(Exception, rf"Error loading model definition from {test_fname}: boom"):
                    register_litellm_models([test_fname])
