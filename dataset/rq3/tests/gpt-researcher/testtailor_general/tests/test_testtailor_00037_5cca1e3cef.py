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
        """Ensure get_llm imports GenericLLMProvider and forwards args to from_provider."""
        with patch("gpt_researcher.llm_provider.GenericLLMProvider.from_provider") as mock_from:
            mock_from.return_value = "generic-provider-instance"

            # import inside the test to use the real function under test
            from gpt_researcher.utils.llm import get_llm

            result = get_llm("openai", api_key="sk-test", region="us-west-2", extra_flag=True)

            # return value is propagated
            self.assertEqual(result, "generic-provider-instance")

            # from_provider was called with the provider name and the exact kwargs
            mock_from.assert_called_once_with(
                "openai", api_key="sk-test", region="us-west-2", extra_flag=True
            )
