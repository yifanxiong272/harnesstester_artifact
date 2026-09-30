import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.routes.mcp')
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
        """complete the test case here"""
        conversation_id = "conv-1"
        user_id = "user-1"

        # Minimal conversation-like object with mutable pr_number list
        class DummyConversation:
            def __init__(self):
                self.pr_number = []

        conv = DummyConversation()

        # Create a fake store with async get_metadata and save_metadata
        store = type("Store", (), {})()

        async def fake_get_metadata(cid):
            # ensure the passed conversation_id is forwarded correctly
            assert cid == conversation_id
            return conv

        async def fake_save_metadata(metadata):
            # simple no-op for save
            assert metadata is conv
            return None

        store.get_metadata = fake_get_metadata
        store.save_metadata = fake_save_metadata

        # fake async get_instance to return our fake store
        async def fake_get_instance(cfg, uid):
            # ensure the user_id is forwarded
            assert uid == user_id
            return store

        # Patch ConversationStoreImpl.get_instance in the module where save_pr_metadata is defined
        convo_store_impl = save_pr_metadata.__globals__['ConversationStoreImpl']
        original_get_instance = convo_store_impl.get_instance
        convo_store_impl.get_instance = fake_get_instance

        try:
            # import asyncio without using an import statement (to comply with test constraints)
            asyncio = __import__('asyncio')

            loop = asyncio.get_event_loop()
            # Case 1: match pull/(\d+)
            loop.run_until_complete(
                save_pr_metadata(user_id, conversation_id, "some url ... pull/123 ...")
            )
            self.assertEqual(conv.pr_number, [123])

            # Case 2: match merge_requests/(\d+)
            loop.run_until_complete(
                save_pr_metadata(user_id, conversation_id, "gitlab link merge_requests/456")
            )
            self.assertEqual(conv.pr_number, [123, 456])

            # Case 3: match pull-requests/(\d+)
            loop.run_until_complete(
                save_pr_metadata(user_id, conversation_id, "other host pull-requests/789 done")
            )
            self.assertEqual(conv.pr_number, [123, 456, 789])

            # Case 4: no match should not change list
            loop.run_until_complete(
                save_pr_metadata(user_id, conversation_id, "no pull id here")
            )
            self.assertEqual(conv.pr_number, [123, 456, 789])
        finally:
            # restore original to avoid side effects on other tests
            convo_store_impl.get_instance = original_get_instance
