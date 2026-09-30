import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.parser')
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
        """Test extraction of JSON when failed_generation is wrapped in code fences and has surrounding tags."""
        # Create a fake error object with the expected structure
        class DummyError:
            def __init__(self, body):
                self.body = body
                # Provide a response attribute just in case it's referenced elsewhere
                class Resp:
                    text = "dummy"
                self.response = Resp()

        # Provide an output_format with a model_validate method expected by the function
        class OutputFormat:
            @staticmethod
            def model_validate(d):
                # For testing, just return the parsed dict so we can assert easily
                return d

        # Construct a failed_generation string that includes header-like tags and a JSON code block
        failed_generation = (
            "<|header_start|>assistant<|header_end|>"
            "```json\n"
            "{\"foo\": \"bar\"}\n"
            "```\n"
            "<function=AgentOutput>"
        )

        error = DummyError({"error": {"failed_generation": failed_generation}})

        result = try_parse_groq_failed_generation(error, OutputFormat)

        # Expect the JSON inside the code block to be parsed correctly
        self.assertEqual(result, {"foo": "bar"})
