import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.writer')
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
        """Test that write_sections builds the prompt including guidelines and calls call_model with expected args."""
        research_state = {
            "title": "Test Topic",
            "research_data": {"finding": "Some important finding"},
            "task": {
                "follow_guidelines": True,
                "guidelines": "Be concise and use formal tone.",
                "model": "test-model",
                "verbose": False,
            },
        }

        # Prepare to monkeypatch call_model in the module where WriterAgent is defined
        sys_mod = __import__("sys")
        agent_module = sys_mod.modules[WriterAgent.__module__]
        original_call_model = getattr(agent_module, "call_model", None)

        async def fake_call_model(prompt_arg, model_arg, response_format=None):
            # Basic assertions about what write_sections should pass through
            assert isinstance(prompt_arg, list), "prompt should be a list"
            joined = " ".join(
                item.get("content", "") for item in prompt_arg if isinstance(item, dict)
            )
            assert "Test Topic" in joined, "Title should be present in prompt content"
            assert "Some important finding" in joined or str(
                research_state["research_data"]
            ) in joined, "Research data should be present in prompt content"
            assert (
                research_state["task"]["guidelines"] in joined
            ), "Guidelines should be included in prompt when follow_guidelines is True"

            # Check model and response_format forwarded correctly
            assert model_arg == "test-model"
            assert response_format == "json"

            # Return a plausible JSON-like structure as the model would
            return {
                "table_of_contents": "- Introduction\n- Conclusion",
                "introduction": "This is an introduction. ([Example](https://example.com))",
                "conclusion": "This is a conclusion. ([Example](https://example.com))",
                "sources": ["- Example, 2026, Author [https://example.com](https://example.com)"],
            }

        # Patch the call_model in the agent's module
        setattr(agent_module, "call_model", fake_call_model)

        try:
            agent = WriterAgent()
            # Run the async method
            asyncio_mod = __import__("asyncio")
            loop = asyncio_mod.get_event_loop()
            result = loop.run_until_complete(agent.write_sections(research_state))

            # Validate result matches fake_call_model return
            self.assertIsInstance(result, dict)
            self.assertIn("introduction", result)
            self.assertIn("conclusion", result)
            self.assertIn("table_of_contents", result)
            self.assertIn("sources", result)
            self.assertTrue(result["introduction"].startswith("This is an introduction"))
            self.assertTrue(result["conclusion"].startswith("This is a conclusion"))
        finally:
            # Restore original call_model in the agent's module
            if original_call_model is not None:
                setattr(agent_module, "call_model", original_call_model)
            else:
                if hasattr(agent_module, "call_model"):
                    delattr(agent_module, "call_model")
