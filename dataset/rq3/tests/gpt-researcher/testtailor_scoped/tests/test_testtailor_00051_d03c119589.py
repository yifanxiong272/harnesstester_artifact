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
        """Ensure call_model constructs Config and calls convert_openai_messages before calling the LLM."""
        prompt = [{"role": "user", "content": "hello"}]

        # Patch create_chat_completion and convert_openai_messages in the module where call_model is defined.
        create_target = f"{call_model.__module__}.create_chat_completion"
        conv_target = f"{call_model.__module__}.convert_openai_messages"

        async_mock = unittest.mock.AsyncMock(return_value="model-response")
        with unittest.mock.patch(create_target, new=async_mock) as mock_create, \
             unittest.mock.patch(conv_target) as mock_convert:
            # Make convert_openai_messages return a list of messages as the LLM helper expects
            mock_convert.return_value = [{"role": "user", "content": "converted"}]

            # Use __import__ to get asyncio without adding an import statement at the top
            asyncio = __import__("asyncio")
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(call_model(prompt=prompt, model="test-model"))
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
                # Clear the event loop to avoid side effects in the test runner
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass

            # Assertions: convert_openai_messages was called with the original prompt
            mock_convert.assert_called_once_with(prompt)
            # create_chat_completion was awaited and its return value propagated
            mock_create.assert_awaited_once()
            self.assertEqual(result, "model-response")
