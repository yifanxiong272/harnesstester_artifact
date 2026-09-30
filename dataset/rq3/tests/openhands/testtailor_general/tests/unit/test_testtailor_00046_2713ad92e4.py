import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.listen_socket')
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
        """Ensure connect reads QUERY_STRING and proceeds without raising (happy path)."""
        environ = {'QUERY_STRING': 'latest_event_id=3&conversation_id=conv1&providers_set=github,gitlab'}
        connection_id = 'conn-123'

        # Get the module where connect is defined without importing sys
        mod = __import__(connect.__module__, fromlist=['*'])

        # Backup originals to restore later
        originals = {}
        names_to_patch = [
            'create_conversation_validator',
            '_invalid_session_api_key',
            'AsyncEventStoreWrapper',
            'EventStore',
            'setup_init_conversation_settings',
            'conversation_manager',
            'sio',
        ]
        for name in names_to_patch:
            originals[name] = getattr(mod, name, None)

        # Stubs
        class DummyValidator:
            async def validate(self, conversation_id, cookies_str, authorization_header):
                return 'user-xyz'

        def dummy_create_conversation_validator():
            return DummyValidator()

        def dummy_invalid_session_api_key(qp):
            return False

        class DummyAsyncEventStoreWrapper:
            def __init__(self, event_store, *args, **kwargs):
                pass

            async def __aiter__(self):
                # make this an async generator that yields nothing
                if False:
                    yield None
                return

        class DummyEventStore:
            def __init__(self, conversation_id, file_store, user_id):
                self.sid = conversation_id
                self.file_store = file_store
                self.user_id = user_id

        async def dummy_setup_init_conversation_settings(user_id, conversation_id, providers_set):
            # Return a simple dict acceptable to join_conversation
            return {}

        class DummyConversationManager:
            file_store = object()

            async def join_conversation(self, conversation_id, connection_id, conversation_init_data, user_id):
                return {'joined': True}

        class DummySio:
            async def emit(self, *args, **kwargs):
                return None

            async def disconnect(self, connection_id):
                return None

        # Apply patches
        mod.create_conversation_validator = dummy_create_conversation_validator
        mod._invalid_session_api_key = dummy_invalid_session_api_key
        mod.AsyncEventStoreWrapper = DummyAsyncEventStoreWrapper
        mod.EventStore = DummyEventStore
        mod.setup_init_conversation_settings = dummy_setup_init_conversation_settings
        mod.conversation_manager = DummyConversationManager()
        mod.sio = DummySio()

        try:
            # Run the async connect function
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(connect(connection_id, environ))
            # connect returns None on success
            self.assertIsNone(result)
        finally:
            # Restore originals
            for name, val in originals.items():
                if val is None:
                    if hasattr(mod, name):
                        delattr(mod, name)
                else:
                    setattr(mod, name, val)
