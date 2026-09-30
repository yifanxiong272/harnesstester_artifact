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
        """Test that GenericLLMProvider.from_provider is used with provider kwargs
        and that a simple LLM response without tool calls is returned.
        """
        # Obtain the function under test from globals (the test harness should have injected it)
        create_fn = globals().get("create_chat_completion_with_tools")
        self.assertIsNotNone(create_fn, "create_chat_completion_with_tools must be available in globals()")

        import sys
        import types
        import asyncio

        # Determine the absolute module name that the relative import inside the function will resolve to.
        # The function does: from ..llm_provider.generic.base import GenericLLMProvider
        # Resolve that using the function's module package.
        func_module = sys.modules[create_fn.__module__]
        package = getattr(func_module, "__package__", None)
        self.assertTrue(package, "Function's module must have a __package__ to resolve relative imports")
        parent_pkg = package.rsplit(".", 1)[0]  # go up one level for ".."
        abs_module_name = f"{parent_pkg}.llm_provider.generic.base"

        # Prepare a fake module with GenericLLMProvider that records calls and returns a fake LLM
        captured = {}

        class FakeProviderClass:
            def __init__(self, name):
                # Provide an llm attribute with bind_tools returning an object with ainvoke coroutine
                self.llm = self

            @classmethod
            def from_provider(cls, provider_name, **kwargs):
                # Record the values passed in
                captured["provider_name"] = provider_name
                captured["kwargs"] = kwargs
                return cls(provider_name)

            def bind_tools(self, tools):
                # Return an object that has an async ainvoke method that returns a simple response object
                class LLMAgent:
                    async def ainvoke(self_inner, lc_messages):
                        class Resp:
                            content = "simulated response"
                            tool_calls = []  # no tool calls
                        return Resp()
                return LLMAgent()

        fake_mod = types.ModuleType(abs_module_name)
        fake_mod.GenericLLMProvider = FakeProviderClass
        # Insert into sys.modules so the relative import inside the function will succeed
        sys.modules[abs_module_name] = fake_mod

        try:
            # Prepare minimal inputs
            messages = [{"role": "user", "content": "Hello"}]
            tools = []

            # Run the async function in an event loop
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    create_fn(
                        messages=messages,
                        tools=tools,
                        model="test-model",
                        llm_provider="fake-provider",
                        llm_kwargs={"custom": "value"},
                    )
                )
            finally:
                loop.close()
        finally:
            # Clean up the fake module
            del sys.modules[abs_module_name]

        # Assert the function returned the expected simple response and no tool metadata
        self.assertIsInstance(result, tuple)
        content, tool_meta = result
        self.assertEqual(content, "simulated response")
        self.assertEqual(tool_meta, [])

        # Assert GenericLLMProvider.from_provider was called with expected args
        self.assertEqual(captured.get("provider_name"), "fake-provider")
        self.assertIn("model", captured.get("kwargs", {}))
        self.assertEqual(captured["kwargs"]["model"], "test-model")
        self.assertIn("custom", captured["kwargs"])
        self.assertEqual(captured["kwargs"]["custom"], "value")
