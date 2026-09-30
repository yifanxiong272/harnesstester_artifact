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
        """Test that an assistant-role message is converted to an AIMessage and the LLM path returns content without tool calls."""
        types = __import__('types')
        orig_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Intercept the import that requests GenericLLMProvider
            if fromlist and 'GenericLLMProvider' in fromlist:
                fake_mod = types.SimpleNamespace()
                class FakeGenericLLMProvider:
                    @staticmethod
                    def from_provider(llm_provider, **kwargs):
                        class LLMLike:
                            def bind_tools(self, tools):
                                class LLMMock:
                                    async def ainvoke(self, messages):
                                        # Ensure the assistant message content made it into the messages
                                        assert any(getattr(m, "content", None) == "hello from assistant" for m in messages)
                                        return types.SimpleNamespace(content="ok", tool_calls=[])
                                return LLMMock()
                        return types.SimpleNamespace(llm=LLMLike())
                fake_mod.GenericLLMProvider = FakeGenericLLMProvider
                return fake_mod

            # Intercept import of ToolMessage from langchain_core.messages
            if fromlist and 'ToolMessage' in fromlist:
                fake_mod = types.SimpleNamespace()
                class ToolMessage:
                    def __init__(self, content, tool_call_id=None):
                        self.content = content
                        self.tool_call_id = tool_call_id
                fake_mod.ToolMessage = ToolMessage
                return fake_mod

            return orig_import(name, globals, locals, fromlist, level)

        with unittest.mock.patch('builtins.__import__', side_effect=fake_import):
            asyncio = __import__('asyncio')
            result, metadata = asyncio.run(
                create_chat_completion_with_tools(
                    messages=[{"role": "assistant", "content": "hello from assistant"}],
                    tools=[],
                    llm_provider="fake_provider",
                )
            )

        # Validate returned content and that no tool calls metadata were produced
        self.assertEqual(result, "ok")
        self.assertEqual(metadata, [])
