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
        """Ensure parent_query is prepended to query and create_chat_completion is called with combined task."""
        # Local imports via __import__ to avoid adding top-level import statements
        asyncio = __import__("asyncio")
        json = __import__("json")
        unittest_mock = __import__("unittest.mock", fromlist=["mock"])

        # Container to capture messages passed to the fake LLM function
        captured = {"messages": None}

        async def fake_create_chat_completion(*args, **kwargs):
            # Capture the messages argument for assertions
            captured["messages"] = kwargs.get("messages")
            # Return a valid JSON string as the LLM response
            return json.dumps({"server": "TestAgent", "agent_role_prompt": "Test Role Prompt"})

        # Minimal cfg object expected by choose_agent using dynamic type factory
        cfg = type("Cfg", (), {
            "smart_llm_model": "test-model",
            "smart_llm_provider": "test-provider",
            "llm_kwargs": {}
        })()

        # Minimal prompt_family with required method (must accept self when bound)
        prompt_family = type("PF", (), {
            "auto_agent_instructions": (lambda self: "auto-instructions")
        })()

        # Patch the create_chat_completion used inside choose_agent to use our fake implementation
        target = f"{choose_agent.__module__}.create_chat_completion"
        with unittest_mock.patch(target, new=fake_create_chat_completion):
            # Run the async function
            result_agent, result_role = asyncio.get_event_loop().run_until_complete(
                choose_agent(
                    query="child query",
                    cfg=cfg,
                    parent_query="parent context",
                    cost_callback=None,
                    headers=None,
                    prompt_family=prompt_family
                )
            )

        # Assert returned values come from our fake response
        self.assertEqual(result_agent, "TestAgent")
        self.assertEqual(result_role, "Test Role Prompt")

        # Ensure the messages passed to the LLM include the combined query "parent context - child query"
        self.assertIsNotNone(captured["messages"], "create_chat_completion was not called with messages")
        user_message = next((m for m in captured["messages"] if m.get("role") == "user"), None)
        self.assertIsNotNone(user_message, "No user message found in messages passed to LLM")
        self.assertTrue(user_message["content"].startswith("task: "), "User message should start with 'task: '")
        self.assertIn("parent context - child query", user_message["content"])
