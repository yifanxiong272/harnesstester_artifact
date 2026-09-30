import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.llm')
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
        """Ensure get_llm delegates to GenericLLMProvider.from_provider and returns its result."""
        provider_name = "fake-provider"
        sentinel_instance = object()

        # Patch the classmethod that should be called by get_llm.
        with patch("gpt_researcher.llm_provider.GenericLLMProvider.from_provider", return_value=sentinel_instance) as mock_from:
            # Call the function under test with some kwargs that should be forwarded.
            result = get_llm(provider_name, api_key="sekrit", region="eu-west-1")

            # Verify the underlying provider factory was called with exactly the same args.
            mock_from.assert_called_once_with(provider_name, api_key="sekrit", region="eu-west-1")

            # And the returned value is the value produced by the patched factory.
            self.assertIs(result, sentinel_instance)
