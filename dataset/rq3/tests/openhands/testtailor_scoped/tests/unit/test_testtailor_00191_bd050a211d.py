import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.app_conversation.app_conversation_service_base')
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
        """Ensure disabled skills are filtered out before updating the agent."""
        # Minimal fake Skill class for testing
        class FakeSkill:
            def __init__(self, name):
                self.name = name

        # Dummy service implementing abstract methods so it can be instantiated.
        class DummyService(AppConversationServiceBase):
            def __init__(self):
                # satisfy attributes referenced elsewhere; values not used here
                self.init_git_in_empty_workspace = False
                self.user_context = None
                self.captured_skills = None

            # Provide the required abstract methods with simple implementations.
            async def count_app_conversations(self, *args, **kwargs):
                return 0

            async def delete_app_conversation(self, *args, **kwargs):
                return None

            async def export_conversation(self, *args, **kwargs):
                return None

            async def get_app_conversation(self, *args, **kwargs):
                return None

            async def search_app_conversations(self, *args, **kwargs):
                return []

            async def start_app_conversation(self, *args, **kwargs):
                return None

            async def update_app_conversation(self, *args, **kwargs):
                return None

            async def load_and_merge_all_skills(
                self, sandbox, selected_repository, project_dir, agent_server_url
            ):
                # Return a predictable set of skills
                return [FakeSkill("skill_a"), FakeSkill("skill_b"), FakeSkill("skill_c")]

            def _create_agent_with_skills(self, agent, skills):
                # Capture the skills passed in for assertions and return a marker
                self.captured_skills = skills
                return "updated_agent_marker"

        service = DummyService()
        # Agent can be any object; the method will pass it through to _create_agent_with_skills
        agent = object()

        # remote_workspace must have a 'host' attribute used in the method
        remote_workspace = type("RW", (), {"host": "http://agent-server"})

        # Call the async method using asyncio.run to execute the coroutine
        result = __import__("asyncio").run(
            service._load_skills_and_update_agent(
                sandbox=None,
                agent=agent,
                remote_workspace=remote_workspace,
                selected_repository=None,
                project_dir="/project",
                disabled_skills=["skill_b"],  # should cause filtering of skill_b
            )
        )

        # Assert the returned agent is what our override returned
        self.assertEqual(result, "updated_agent_marker")

        # Assert that the captured skills do not include the disabled one
        captured_names = [s.name for s in service.captured_skills]
        self.assertListEqual(captured_names, ["skill_a", "skill_c"])
