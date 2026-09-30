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
        """Ensure fuzzy_match_models skips entries with no litellm_provider (hits the continue)."""
        # Import inside test to rely on test-suite imports/setup
        from aider import models

        # Ensure there is at least one entry so the loop runs, but its provider is empty
        test_meta = {"example-model": {"mode": "chat", "litellm_provider": ""}}

        # Patch the litellm.model_cost mapping and the model_info_manager local metadata
        with patch.dict("aider.models.litellm.model_cost", test_meta, clear=True), patch.object(
            models.model_info_manager, "local_model_metadata", {}
        ):
            # Call the function under test with a name that would otherwise match
            res = models.fuzzy_match_models("example")

            # Because the provider value is empty, the code should hit the 'continue'
            # and return no matches (empty list)
            self.assertEqual(res, [])
