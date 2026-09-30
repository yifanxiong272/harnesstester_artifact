import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.utils.llms')
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
        """Ensure call_model returns parse_json_markdown(...) result when response_format='json'"""
        # Import the module where call_model is defined
        module = __import__(call_model.__module__, fromlist=["*"])

        fake_response = '```json\n{"answer": 42}\n```'
        # Async mock for create_chat_completion
        async_mock = unittest.mock.AsyncMock(return_value=fake_response)
        # Mock parse_json_markdown to return a sentinel parsed object
        mock_parse = unittest.mock.Mock(return_value={"answer": 42})

        # Provide a minimal Config replacement so instantiation is cheap and predictable
        class DummyConfig:
            def __init__(self):
                self.smart_llm_provider = "dummy_provider"
                self.llm_kwargs = {}

        # Ensure convert_openai_messages won't transform input in unpredictable ways
        def identity_convert(msgs):
            return msgs

        with unittest.mock.patch.object(module, "create_chat_completion", new=async_mock):
            with unittest.mock.patch.object(module, "parse_json_markdown", new=mock_parse):
                with unittest.mock.patch.object(module, "Config", new=DummyConfig):
                    with unittest.mock.patch.object(module, "convert_openai_messages", new=identity_convert):
                        # Run the async function without assuming asyncio is imported in the test scope
                        loop = __import__("asyncio").get_event_loop()
                        result = loop.run_until_complete(
                            call_model(prompt=[{"role": "user", "content": "hello"}],
                                       model="dummy-model",
                                       response_format="json")
                        )

        # The return value should be whatever our mocked parse_json_markdown returned
        self.assertEqual(result, {"answer": 42})

        # Ensure the LLM was awaited and parse_json_markdown was called with the response
        async_mock.assert_awaited_once()
        mock_parse.assert_called_once()
        called_args, called_kwargs = mock_parse.call_args
        self.assertEqual(called_args[0], fake_response)
        self.assertIn("parser", called_kwargs)
        self.assertTrue(callable(called_kwargs["parser"]))
