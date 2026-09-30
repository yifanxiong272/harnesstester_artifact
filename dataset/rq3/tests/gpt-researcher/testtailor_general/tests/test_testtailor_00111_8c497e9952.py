import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.tools')
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
        """Ensure calculate_llm_cost is called with the expected transformed inputs
        and that the returned cost is forwarded to the provided callback.
        """
        # Create a simple dummy response object with the expected attributes
        class DummyResponse:
            def __init__(self):
                self.content = "the response"
                self.response_metadata = {"resp_meta": 1}
                self.usage_metadata = {"tokens": 42}

        response = DummyResponse()
        captured = []

        def cost_callback(value):
            captured.append(value)

        expected_return = {"total_cost": 9.99}

        # Patch calculate_llm_cost in the same module as _track_response_cost
        patch_target = f"{_track_response_cost.__module__}.calculate_llm_cost"
        with unittest.mock.patch(patch_target) as mock_calc:
            mock_calc.return_value = expected_return

            _track_response_cost(
                llm_provider="test_provider",
                model="test-model",
                input_payload={"question": "hello"},
                response_message=response,
                request_options={"option": True},
                cost_callback=cost_callback,
            )

            # Ensure calculate_llm_cost was called exactly once
            mock_calc.assert_called_once()
            called_kwargs = mock_calc.call_args.kwargs

            # Verify that the values passed to calculate_llm_cost are as expected
            self.assertEqual(called_kwargs["llm_provider"], "test_provider")
            self.assertEqual(called_kwargs["model"], "test-model")
            self.assertEqual(called_kwargs["input_content"], str({"question": "hello"}))
            # response.content should be used for output_content
            self.assertEqual(called_kwargs["output_content"], str("the response"))
            self.assertEqual(called_kwargs["response_metadata"], {"resp_meta": 1})
            self.assertEqual(called_kwargs["usage_metadata"], {"tokens": 42})
            self.assertEqual(called_kwargs["request_options"], {"option": True})

            # Ensure the callback received the returned cost
            self.assertEqual(captured, [expected_return])
