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
        """Ensure that when json5.loads returns a falsy model_def (empty dict),
        the function continues without registering and returns an empty list."""
        fake_fname = "fake_model.json"

        # Replace the local_model_metadata with a MagicMock so we can assert update wasn't called.
        with patch("os.path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="{}") as mock_read, \
             patch("json5.loads", return_value={}) as mock_json_loads, \
             patch.object(model_info_manager, "local_model_metadata", new=MagicMock()) as mock_local:
            result = register_litellm_models([fake_fname])

            # Since json5.loads returned an empty dict (falsy), no files should be reported loaded.
            self.assertEqual(result, [])

            # read_text should have been called once for the path.
            mock_read.assert_called_once()

            # json5.loads should have been called with the file contents.
            mock_json_loads.assert_called_once_with("{}")

            # The mocked local_model_metadata.update should not have been called because we continued.
            mock_local.update.assert_not_called()
