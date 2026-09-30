import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.app_conversation.live_status_app_conversation_service')
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
        """When parent_conversation_id is provided but parent is missing, raise ValueError and call info service."""
        # Create a dummy user context that returns a user id
        class DummyUserContext:
            async def get_user_id(self):
                return 'test-user'

        # Dummy info service that records the requested id and returns None (not found)
        class DummyAppConversationInfoService:
            def __init__(self):
                self.last_requested = None

            async def get_app_conversation_info(self, conversation_id):
                self.last_requested = conversation_id
                return None

        # Build the start request with a valid UUID string for parent_conversation_id
        request = AppConversationStartRequest(
            parent_conversation_id='00000000-0000-0000-0000-000000000000'
        )

        # Create service instance without calling its constructor and inject only needed dependencies
        svc = object.__new__(LiveStatusAppConversationService)
        svc.user_context = DummyUserContext()
        svc.app_conversation_info_service = DummyAppConversationInfoService()

        # Run the async generator and expect a ValueError about missing parent conversation
        async def run_generator():
            async for _ in svc._start_app_conversation(request):
                pass

        with self.assertRaises(ValueError) as cm:
            asyncio.run(run_generator())

        # Verify the info service was called with the provided parent id
        self.assertEqual(
            svc.app_conversation_info_service.last_requested,
            request.parent_conversation_id,
        )

        # Verify the exception message contains the parent id
        self.assertIn(
            str(request.parent_conversation_id),
            str(cm.exception),
        )
