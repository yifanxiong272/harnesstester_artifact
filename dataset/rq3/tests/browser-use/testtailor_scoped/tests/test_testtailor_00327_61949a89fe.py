import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.chat')
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
        """Ensure that when ChatDeepSeek.top_p is set it is forwarded to the provider call."""
        async def run_test():
            seen = {}

            # small helper to build simple objects without imports
            class O:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            async def create(model=None, messages=None, **kwargs):
                # capture what was passed to the provider
                seen['model'] = model
                seen['messages'] = messages
                seen['kwargs'] = kwargs
                # mimic provider response shape
                return O(choices=[O(message=O(content="ok"))])

            # dummy client with chat.completions.create async function
            dummy_client = O()
            dummy_client.chat = O(completions=O(create=create))

            # instantiate ChatDeepSeek with top_p set so the code path sets common['top_p']
            chat = ChatDeepSeek(top_p=0.42)
            # patch _client to return our dummy client
            chat._client = lambda: dummy_client

            # call ainvoke (no output_format and no tools => regular multi-turn path)
            result = await chat.ainvoke([])

            # assertions: completion returned and top_p forwarded
            self.assertEqual(result.completion, "ok")
            self.assertIn('top_p', seen['kwargs'])
            self.assertEqual(seen['kwargs']['top_p'], 0.42)

        __import__('asyncio').run(run_test())
