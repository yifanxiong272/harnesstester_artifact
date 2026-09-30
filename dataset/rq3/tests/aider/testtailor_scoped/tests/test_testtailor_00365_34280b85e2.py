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
        """Ensure print_matching_models writes the 'no matches' message when fuzzy_match_models returns empty."""
        from unittest.mock import MagicMock, patch
        import aider.models as models

        mock_io = MagicMock()

        with patch("aider.models.fuzzy_match_models", return_value=[]):
            models.print_matching_models(mock_io, "no-such-model")

        mock_io.tool_output.assert_called_once_with('No models match "no-such-model".')
