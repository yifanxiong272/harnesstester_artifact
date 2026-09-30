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
        """Ensure a 'system' role message is converted to a SystemMessage and used by the LLM."""
        # Prepare a dummy SystemMessage/HumanMessage/AIMessage classes and inject into function globals
        def _make_msg_class(name):
            return type(name, (), {"__init__": lambda self, content: setattr(self, "content", content), "__repr__": lambda self: f"<{name} content={getattr(self,'content',None)}>"})
        SystemMessage = _make_msg_class("SystemMessage")
        HumanMessage = _make_msg_class("HumanMessage")
        AIMessage = _make_msg_class("AIMessage")

        # Inject into the function's globals so the function will use these classes
        create_chat_completion_with_tools.__globals__["SystemMessage"] = SystemMessage
        create_chat_completion_with_tools.__globals__["HumanMessage"] = HumanMessage
        create_chat_completion_with_tools.__globals__["AIMessage"] = AIMessage

        # Keep a reference to the real __import__ to delegate other imports
        real_import = __import__

        # Create fake modules/classes to satisfy runtime imports inside the function
        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Handle import of the llm provider module
            if "llm_provider.generic.base" in name:
                # Create a fake GenericLLMProvider class with a from_provider method
                class FakeLLM:
                    def __init__(self):
                        pass

                    def bind_tools(self, tools):
                        # Return an object that has ainvoke method (async)
                        return self

                    async def ainvoke(self, messages):
                        # Return an object with a content attribute that reflects the first message content
                        first_content = ""
                        if messages:
                            first = messages[0]
                            first_content = getattr(first, "content", str(first))
                        return type("Resp", (), {"content": f"OK:{first_content}", "tool_calls": []})()

                class GenericLLMProvider:
                    @staticmethod
                    def from_provider(provider_name, **kwargs):
                        return type("Prov", (), {"llm": FakeLLM()})()

                mod = type("M", (), {})()
                setattr(mod, "GenericLLMProvider", GenericLLMProvider)
                return mod

            # Handle import of langchain_core.messages (ToolMessage)
            if "langchain_core.messages" in name:
                class ToolMessage:
                    def __init__(self, content, tool_call_id=None):
                        self.content = content
                        self.tool_call_id = tool_call_id

                mod = type("M", (), {})()
                setattr(mod, "ToolMessage", ToolMessage)
                return mod

            # Delegate all other imports to the real importer
            return real_import(name, globals, locals, fromlist, level)

        # Patch builtins.__import__ so the function's internal imports succeed with our fakes
        with unittest.mock.patch("builtins.__import__", side_effect=fake_import):
            # Prepare input: one message with role 'system' to hit the target branch
            messages = [{"role": "system", "content": "system initialized"}]
            tools = []  # no tools needed for this test

            # Call the async function
            result = asyncio.run(create_chat_completion_with_tools(messages=messages, tools=tools, cost_callback=None))

        # The fake LLM returns content prefixed with "OK:" and echoes the first message content
        response_content, tool_calls_metadata = result
        self.assertEqual(response_content, "OK:system initialized")
        self.assertEqual(tool_calls_metadata, [])
