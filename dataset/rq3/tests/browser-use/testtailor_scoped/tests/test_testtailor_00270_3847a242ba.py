import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.service')
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
        """Provide a valid llm_screenshot_size tuple and verify Agent accepts it and stores it on the BrowserSession."""
        # Minimal LLM stub satisfying BaseChatModel protocol used during Agent init
        class DummyLLM:
            provider = 'openai'
            model = 'gpt-test-model'

            async def ainvoke(self, messages, output_format=None, **kwargs):
                # Return a minimal object with .completion and .usage attributes to satisfy wrappers
                class Resp:
                    completion = ''
                    usage = None

                return Resp()

        llm = DummyLLM()

        # Pass override_system_message to avoid reading template resource files during SystemPrompt initialization
        agent = Agent(task='validate screenshot size', llm=llm, llm_screenshot_size=(200, 200), override_system_message='override')

        # The constructor should have accepted the tuple and stored it on the browser_session
        self.assertIsNotNone(agent.browser_session)
        self.assertEqual(agent.browser_session.llm_screenshot_size, (200, 200))
