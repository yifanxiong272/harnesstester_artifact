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
        """Verify that when parent_conversation_id is provided we call get_app_conversation_info
        and inherit configuration from the parent before yielding the initial task.
        """
        async def runner():
            # Create instance without calling __init__ (to avoid required constructor args)
            service = object.__new__(LiveStatusAppConversationService)

            # Mock user_context.get_user_id to return a known value
            service.user_context = Mock()
            service.user_context.get_user_id = AsyncMock(return_value='test-user')

            # Prepare a parent AppConversationInfo to be returned by the service
            parent_id = uuid4()
            parent_info = AppConversationInfo(
                id=parent_id,
                created_by_user_id='parent-user',
                sandbox_id='parent-sandbox',
            )

            # Mock app_conversation_info_service.get_app_conversation_info
            service.app_conversation_info_service = Mock()
            service.app_conversation_info_service.get_app_conversation_info = AsyncMock(
                return_value=parent_info
            )

            # Replace _inherit_configuration_from_parent and _apply_suggested_task with spies
            service._inherit_configuration_from_parent = Mock()
            service._apply_suggested_task = Mock()

            # Build request with parent_conversation_id set
            request = AppConversationStartRequest(parent_conversation_id=parent_id)

            # Start the async generator and get the first yielded task
            gen = service._start_app_conversation(request)
            first_task = await gen.__anext__()  # initial created task is yielded here

            # NOTE: Do not close the generator; closing may resume startup logic that depends
            # on many other services. Leaving it unclosed is acceptable for this unit test.

            # Assertions: get_app_conversation_info was awaited with the parent id
            service.app_conversation_info_service.get_app_conversation_info.assert_awaited_once_with(
                parent_id
            )

            # Ensure we attempted to inherit configuration from the parent
            service._inherit_configuration_from_parent.assert_called_once_with(
                request, parent_info
            )

            # Validate the yielded task contains the request we passed
            self.assertIsInstance(first_task, AppConversationStartTask)
            self.assertIs(first_task.request, request)
            self.assertEqual(first_task.created_by_user_id, 'test-user')

        asyncio.run(runner())
