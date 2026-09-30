import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.agent_creator')
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
        """Ensure parent_query is concatenated into the task message and JSON response is parsed."""
        # Arrange
        q = "find relevant studies on X"
        parent = "broader topic Y"

        class Cfg:
            pass

        cfg = Cfg()
        cfg.smart_llm_model = "test-model"
        cfg.smart_llm_provider = "test-provider"
        cfg.llm_kwargs = {"foo": "bar"}

        class FakePromptFamily:
            def auto_agent_instructions(self):
                return "Be concise."

        json = __import__("json")

        async def fake_create_chat_completion(model, messages, temperature, llm_provider, llm_kwargs, cost_callback=None, **kwargs):
            # validate that parent_query has been concatenated into the user message
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("Be concise.", messages[0]["content"])
            self.assertEqual(messages[1]["role"], "user")
            expected_task = f"task: {parent} - {q}"
            self.assertEqual(messages[1]["content"], expected_task)
            # return a valid JSON string as the LLM would
            return json.dumps({"server": "AgentX", "agent_role_prompt": "Role prompt"})

        # Patch the create_chat_completion used by choose_agent
        choose_agent_globals = choose_agent.__globals__
        original_create = choose_agent_globals.get("create_chat_completion")
        choose_agent_globals["create_chat_completion"] = fake_create_chat_completion

        try:
            # Use built-in __import__ to get asyncio without adding an import statement
            asyncio = __import__("asyncio")

            # Act
            result = asyncio.get_event_loop().run_until_complete(
                choose_agent(
                    q,
                    cfg,
                    parent_query=parent,
                    cost_callback=None,
                    headers=None,
                    prompt_family=FakePromptFamily()
                )
            )

            # Assert
            self.assertEqual(result, ("AgentX", "Role prompt"))
        finally:
            # Restore original
            if original_create is not None:
                choose_agent_globals["create_chat_completion"] = original_create
