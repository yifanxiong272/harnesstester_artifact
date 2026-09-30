import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.services.conversation_service')
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
        """Test that a new conversation_id is generated when None is passed and metadata is saved."""
        async def _run():
            # Prepare a fake conversation store instance with async methods
            conversation_store_mock = MagicMock()
            conversation_store_mock.exists = AsyncMock(return_value=False)
            conversation_store_mock.save_metadata = AsyncMock()
            conversation_store_mock.get_metadata = AsyncMock()

            # Patch ConversationStoreImpl.get_instance to return our fake store
            with patch.object(ConversationStoreImpl, "get_instance", new_callable=AsyncMock) as mocked_get_instance:
                mocked_get_instance.return_value = conversation_store_mock

                # Call the async function under test with conversation_id=None to force new id generation
                result = await initialize_conversation(
                    user_id="test_user",
                    conversation_id=None,
                    selected_repository="my/repo",
                    selected_branch="main",
                    conversation_trigger=ConversationTrigger.GUI,
                    git_provider=ProviderType.GITHUB,
                )

                # Ensure get_instance was awaited and called with config and the provided user_id
                mocked_get_instance.assert_awaited_once()
                # Ensure exists was awaited once with the generated conversation id
                conversation_store_mock.exists.assert_awaited_once_with(result.conversation_id)
                # Ensure save_metadata was awaited exactly once
                self.assertEqual(conversation_store_mock.save_metadata.await_count, 1)

                # Inspect the saved metadata argument
                saved_meta = conversation_store_mock.save_metadata.await_args.args[0]
                # The saved metadata should match the returned metadata
                self.assertEqual(saved_meta.conversation_id, result.conversation_id)
                self.assertEqual(saved_meta.user_id, "test_user")
                self.assertEqual(saved_meta.selected_repository, "my/repo")
                self.assertEqual(saved_meta.selected_branch, "main")
                self.assertEqual(saved_meta.git_provider, ProviderType.GITHUB)
                # Title should be the default based on the generated id
                expected_title = get_default_conversation_title(result.conversation_id)
                self.assertEqual(saved_meta.title, expected_title)
                self.assertEqual(result.title, expected_title)

        # Use __import__ to avoid adding a top-level import statement for asyncio
        __import__('asyncio').run(_run())
