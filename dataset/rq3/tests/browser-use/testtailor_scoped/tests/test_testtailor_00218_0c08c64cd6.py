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
        """Agent __init__ should raise ValueError when llm_screenshot_size is not a tuple of two ints."""
        # Minimal fake LLM implementing the interface pieces Agent expects during init
        class FakeLLM:
            provider = 'fake-provider'
            model = 'fake-model'

            async def ainvoke(self, messages, output_format=None, **kwargs):
                class Result:
                    completion = ''
                    usage = None
                return Result()

        fake_llm = FakeLLM()

        # Pass a list instead of a tuple to trigger the validation error
        with self.assertRaises(ValueError) as cm:
            Agent(task='do something', llm=fake_llm, llm_screenshot_size=[200, 150])

        self.assertIn('llm_screenshot_size must be a tuple of (width, height)', str(cm.exception))
