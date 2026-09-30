import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.sandbox.remote_sandbox_service')
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
        """Ensure poll_agent_servers performs its initial agent-server /list fetch
        and can be cancelled cleanly while exercising the inner 'from ...config import ...'
        import path inside the coroutine."""
        # Import locally to avoid relying on top-level imports in the test harness.
        import sys
        import types
        import asyncio

        # Keep reference to original module if present so we can restore it.
        orig_mod = sys.modules.get('openhands.app_server.config')
        fake_mod = types.ModuleType('openhands.app_server.config')

        # Track calls to the httpx client's get method to assert behavior.
        httpx_get_calls: list[str] = []

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                # Return one running runtime to exercise the code path that
                # creates runtimes_by_sandbox_id. There will be no conversations
                # yielded so refresh_conversation won't be invoked.
                return {
                    'runtimes': [
                        {
                            'session_id': 'sandbox-1',
                            'status': 'running',
                            'url': 'http://agent.local',
                            'session_api_key': 'sess-key-1',
                        }
                    ]
                }

        class FakeHTTPXClient:
            async def get(self, url, headers=None, params=None):
                # Record the URL being fetched and return a fake response for /list.
                httpx_get_calls.append(url)
                return FakeResponse()

        class AsyncCM:
            def __init__(self, result):
                self._result = result

            async def __aenter__(self):
                return self._result

            async def __aexit__(self, exc_type, exc, tb):
                return False

        # Provide get_httpx_client which returns an async context manager yielding our fake client.
        def get_httpx_client(state):
            return AsyncCM(FakeHTTPXClient())

        # Provide app conversation info service with a search method that yields nothing.
        class FakeAppConversationInfoService:
            async def search_app_conversation_info(self, *args, **kwargs):
                # Make this an async generator that yields nothing.
                if False:
                    yield
                return

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def save_app_conversation_info(self, info):
                return info

        def get_app_conversation_info_service(state):
            return AsyncCM(FakeAppConversationInfoService())

        # Provide minimal event and callback services (not exercised because there are no conversations).
        class FakeEventService:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get_event(self, conversation_id, event_id):
                return None

            async def save_event(self, conversation_id, event):
                return None

        def get_event_service(state):
            return AsyncCM(FakeEventService())

        class FakeEventCallbackService:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def execute_callbacks(self, conversation_id, event):
                return None

        def get_event_callback_service(state):
            return AsyncCM(FakeEventCallbackService())

        # Attach our fake callables to the fake module and insert into sys.modules.
        fake_mod.get_httpx_client = get_httpx_client
        fake_mod.get_app_conversation_info_service = get_app_conversation_info_service
        fake_mod.get_event_service = get_event_service
        fake_mod.get_event_callback_service = get_event_callback_service
        sys.modules['openhands.app_server.config'] = fake_mod

        async def runner():
            # Start the polling coroutine and let it run briefly, then cancel it.
            task = asyncio.create_task(poll_agent_servers('http://api.local', 'api-key', 0.05))
            # Give it a moment to perform the first /list fetch.
            await asyncio.sleep(0.12)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # Expected due to cancellation
                pass

        try:
            asyncio.run(runner())
            # Ensure that at least one HTTP GET was attempted (the /list call).
            self.assertTrue(any('/list' in url for url in httpx_get_calls))
        finally:
            # Restore original module if present, otherwise remove our fake.
            if orig_mod is not None:
                sys.modules['openhands.app_server.config'] = orig_mod
            else:
                if 'openhands.app_server.config' in sys.modules:
                    del sys.modules['openhands.app_server.config']
