import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.app_conversation.app_conversation_router')
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
        """Return a 404 JSONResponse when the sandbox exists but is not RUNNING."""
        async def run():
            # Use a simple string as the conversation id to avoid needing uuid imports
            conversation_id = 'conv-1'

            # Dummy conversation with a sandbox_id
            class DummyConversation:
                def __init__(self, sandbox_id):
                    self.sandbox_id = sandbox_id

            dummy_conversation = DummyConversation(sandbox_id='sandbox-1')

            # Dummy sandbox in a non-RUNNING state (e.g., STARTING)
            class DummySandbox:
                def __init__(self):
                    self.id = 'sandbox-1'
                    self.sandbox_spec_id = 'spec-1'
                    # Use a string status that will not equal SandboxStatus.RUNNING
                    self.status = 'STARTING'
                    self.exposed_urls = []
                    self.session_api_key = None

            dummy_sandbox = DummySandbox()

            # Services with the minimal async methods the target function will call
            class DummyAppConversationService:
                async def get_app_conversation(self, conv_id):
                    # Return the conversation we set up regardless of conv_id
                    return dummy_conversation

            class DummySandboxService:
                async def get_sandbox(self, sandbox_id):
                    return dummy_sandbox

            class DummySandboxSpecService:
                async def get_sandbox_spec(self, sandbox_spec_id):
                    return None
                async def get_default_sandbox_spec(self):
                    return None

            app_conv_service = DummyAppConversationService()
            sandbox_service = DummySandboxService()
            sandbox_spec_service = DummySandboxSpecService()

            result = await _get_agent_server_context(
                conversation_id,
                app_conv_service,
                sandbox_service,
                sandbox_spec_service,
            )

            # Should be a JSONResponse with 404 status and an error mentioning the conversation id
            self.assertIsInstance(result, JSONResponse)
            self.assertEqual(result.status_code, 404)

            # Extract body text and ensure it mentions the conversation id
            if hasattr(result, 'body') and result.body is not None:
                body_text = result.body.decode()
            else:
                # fallback to render() if body not present
                body_text = result.render().decode()

            self.assertIn(str(conversation_id), body_text)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run())
        finally:
            loop.close()
