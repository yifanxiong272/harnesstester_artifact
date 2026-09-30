import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.costs')
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
        """Ensure inference_geo is normalized and the US multiplier is applied only for matching models."""
        # Mixed-case inference_geo should be normalized to lower-case and match "us"
        multiplier = _get_anthropic_pricing_multiplier(
            model_name="claude-opus-4-7",
            request_options={"inference_geo": "Us"},
        )
        self.assertEqual(multiplier, 1.1)

        # If inference_geo is not "us", multiplier should remain 1.0 even for a US model name
        multiplier_non_us = _get_anthropic_pricing_multiplier(
            model_name="claude-opus-4-7",
            request_options={"inference_geo": "eu"},
        )
        self.assertEqual(multiplier_non_us, 1.0)

        # If inference_geo is "us" but model does not match any US-specific models, multiplier is 1.0
        multiplier_non_matching_model = _get_anthropic_pricing_multiplier(
            model_name="claude-unknown-1",
            request_options={"inference_geo": "US"},
        )
        self.assertEqual(multiplier_non_matching_model, 1.0)
