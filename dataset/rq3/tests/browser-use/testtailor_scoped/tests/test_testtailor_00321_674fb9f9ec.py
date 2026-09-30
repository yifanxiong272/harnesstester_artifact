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
    def test_llm_screenshot_size_non_integer_dimensions_raises(self):
        """Provide a non-integer dimension in llm_screenshot_size and assert ValueError is raised."""
        # Minimal dummy LLM implementing the shape the Agent expects
        class DummyLLM:
            provider = 'openai'
            model = 'gpt-test'

            async def ainvoke(self, messages, output_format=None, **kwargs):
                class Resp:
                    completion = None
                    usage = None
                return Resp()

        dummy_llm = DummyLLM()

        # Width is a float -> should trigger the integer-dimension validation error
        with self.assertRaisesRegex(ValueError, 'llm_screenshot_size dimensions must be integers'):
            Agent(task='noop', llm=dummy_llm, llm_screenshot_size=(100.5, 200))
