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
        """complete the test case here"""
        # Prepare a fake response message with content and metadata
        class DummyResponse:
            def __init__(self):
                self.content = "response text"
                self.response_metadata = {"rmeta": 123}
                self.usage_metadata = {"tokens": 5}

        response_msg = DummyResponse()
        input_payload = {"key": "value"}
        request_options = {"opt": True}

        # Prepare a fake calculate_llm_cost to capture call parameters and return a known value
        captured = {}

        def fake_calculate_llm_cost(
            *,
            llm_provider,
            model,
            input_content,
            output_content,
            response_metadata,
            usage_metadata,
            request_options: dict,
        ):
            captured["llm_provider"] = llm_provider
            captured["model"] = model
            captured["input_content"] = input_content
            captured["output_content"] = output_content
            captured["response_metadata"] = response_metadata
            captured["usage_metadata"] = usage_metadata
            captured["request_options"] = request_options
            return {"cost": 0.123}

        # Patch the calculate_llm_cost used by _track_response_cost via its globals dict
        func_globals = _track_response_cost.__globals__
        original_calculate = func_globals.get("calculate_llm_cost")
        func_globals["calculate_llm_cost"] = fake_calculate_llm_cost

        # Prepare a cost callback to capture the value passed to it
        cost_calls = []

        def cost_callback(value):
            cost_calls.append(value)

        try:
            # Call the function under test
            _track_response_cost(
                llm_provider="prov-x",
                model="model-y",
                input_payload=input_payload,
                response_message=response_msg,
                request_options=request_options,
                cost_callback=cost_callback,
            )

            # Assertions: calculate_llm_cost was called with expected transformed values
            self.assertEqual(captured.get("llm_provider"), "prov-x")
            self.assertEqual(captured.get("model"), "model-y")
            self.assertEqual(captured.get("input_content"), str(input_payload))
            self.assertEqual(captured.get("output_content"), str(response_msg.content))
            self.assertEqual(captured.get("response_metadata"), response_msg.response_metadata)
            self.assertEqual(captured.get("usage_metadata"), response_msg.usage_metadata)
            self.assertIs(captured.get("request_options"), request_options)

            # Assertions: cost_callback was invoked with the returned llm cost
            self.assertEqual(cost_calls, [{"cost": 0.123}])
        finally:
            # Restore original function to avoid side effects on other tests
            if original_calculate is None:
                func_globals.pop("calculate_llm_cost", None)
            else:
                func_globals["calculate_llm_cost"] = original_calculate
