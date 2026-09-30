import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.routes.manage_conversations')
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
        """Test building a ConversationInfoResultSet with connections and agent loop info."""
        types = __import__('types')
        datetime_mod = __import__('datetime')
        asyncio = __import__('asyncio')
        SimpleNamespace = types.SimpleNamespace

        # Two conversation IDs: one without a title (will use default), one with a title
        conv_id_1 = 'abcde12345'
        conv_id_2 = 'fghij67890'

        conv1 = SimpleNamespace(
            conversation_id=conv_id_1,
            title=None,
            last_updated_at=None,
            created_at=datetime_mod.datetime.now(datetime_mod.timezone.utc),
            selected_repository=None,
            selected_branch=None,
            git_provider=None,
            trigger=None,
            pr_number=[],
        )
        conv2 = SimpleNamespace(
            conversation_id=conv_id_2,
            title='My Custom Title',
            last_updated_at=None,
            created_at=datetime_mod.datetime.now(datetime_mod.timezone.utc),
            selected_repository=None,
            selected_branch=None,
            git_provider=None,
            trigger=None,
            pr_number=[],
        )

        # Fake manager with async methods
        class FakeManager:
            async def get_connections(self, filter_to_sids):
                return {
                    'connA': conv_id_1,
                    'connB': conv_id_1,
                    'connC': conv_id_2,
                }

            async def get_agent_loop_info(self, filter_to_sids):
                # Provide agent loop info only for conv1
                return [
                    SimpleNamespace(
                        conversation_id=conv_id_1,
                        url='http://loop/conv1',
                        session_api_key='key-1',
                        event_store=None,
                        status=_get_conversation_info.__globals__['ConversationStatus'].RUNNING,
                        runtime_status=_get_conversation_info.__globals__['RuntimeStatus'].READY,
                    )
                ]

        # Inject fake manager into target globals
        target_globals = _build_conversation_result_set.__globals__
        had_original = 'conversation_manager' in target_globals
        original_manager = target_globals.get('conversation_manager', None)
        target_globals['conversation_manager'] = FakeManager()

        try:
            # Create and use a fresh event loop to avoid nested-loop issues in test runner
            loop = asyncio.new_event_loop()
            try:
                old_loop = None
                try:
                    old_loop = asyncio.get_event_loop()
                except Exception:
                    old_loop = None
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    _build_conversation_result_set([conv1, conv2], next_page_id='next123')
                )
            finally:
                loop.close()
                # restore previous loop if any
                try:
                    asyncio.set_event_loop(old_loop)
                except Exception:
                    # best effort restore; ignore if not possible
                    pass

            # Basic assertions on the result set
            self.assertIsNotNone(result)
            self.assertEqual(result.next_page_id, 'next123')
            self.assertEqual(len(result.results), 2)

            helper_globals = _get_conversation_info.__globals__
            get_default_title = helper_globals['get_default_conversation_title']
            ConversationStatus = helper_globals['ConversationStatus']
            RuntimeStatus = helper_globals['RuntimeStatus']

            # First result corresponds to conv1 (default title, 2 connections, has agent loop info)
            info1 = result.results[0]
            self.assertEqual(info1.conversation_id, conv_id_1)
            self.assertEqual(info1.title, get_default_title(conv_id_1))
            self.assertEqual(info1.num_connections, 2)
            self.assertEqual(info1.status, ConversationStatus.RUNNING)
            self.assertEqual(info1.runtime_status, RuntimeStatus.READY)
            self.assertEqual(info1.url, 'http://loop/conv1')
            self.assertEqual(info1.session_api_key, 'key-1')

            # Second result corresponds to conv2 (custom title, 1 connection, no agent loop info -> STOPPED)
            info2 = result.results[1]
            self.assertEqual(info2.conversation_id, conv_id_2)
            self.assertEqual(info2.title, 'My Custom Title')
            self.assertEqual(info2.num_connections, 1)
            self.assertEqual(info2.status, ConversationStatus.STOPPED)
            self.assertIsNone(info2.runtime_status)
            self.assertIsNone(info2.url)
            self.assertIsNone(info2.session_api_key)
        finally:
            # Restore original manager state
            if had_original:
                target_globals['conversation_manager'] = original_manager
            else:
                if 'conversation_manager' in target_globals:
                    del target_globals['conversation_manager']
