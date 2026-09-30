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
        model_fname = "fake_model.json"

        # Make os.path.exists return True so the loop enters the try block,
        # and make Path.read_text raise an error to trigger the except branch.
        with patch("os.path.exists", return_value=True), patch(
            "pathlib.Path.read_text", side_effect=ValueError("boom")
        ):
            with self.assertRaises(Exception) as cm:
                register_litellm_models([model_fname])

            expected_msg = f"Error loading model definition from {model_fname}: boom"
            self.assertEqual(str(cm.exception), expected_msg)
