import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
    @patch("aider.analytics.model_info_manager.get_model_from_cached_json_db")
    def test_case_XX(self, mock_get):
        """Ensure _redact_model_name queries the model_info_manager and redacts unknown models."""
        analytics = Analytics()

        # Case 1: model is known (info truthy) -> return full model name
        mock_get.return_value = {"some": "info"}
        model_known = type("Model", (), {"name": "openai/gpt-4"})()
        self.assertEqual(analytics._redact_model_name(model_known), "openai/gpt-4")
        mock_get.assert_called_with("openai/gpt-4")

        # Case 2: model is unknown and contains a provider slash -> redact part after slash
        mock_get.reset_mock()
        mock_get.return_value = None
        model_unknown_slash = type("Model", (), {"name": "provider/sensitive-model"})()
        self.assertEqual(analytics._redact_model_name(model_unknown_slash), "provider/REDACTED")
        mock_get.assert_called_with("provider/sensitive-model")

        # Case 3: model is unknown and has no slash -> return None
        mock_get.reset_mock()
        model_unknown_noslash = type("Model", (), {"name": "nosslashmodel"})()
        self.assertIsNone(analytics._redact_model_name(model_unknown_noslash))
        mock_get.assert_called_with("nosslashmodel")
