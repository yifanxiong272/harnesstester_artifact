import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.page')
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
        """Ensure _ensure_session attaches to target and enables domains when no session_id"""
        calls = {'attach_count': 0, 'attach_params': None, 'enabled_sessions': []}

        class DummySend:
            def __init__(self):
                # provide attributes used in Page._ensure_session
                self.Target = self
                self.Page = self
                self.DOM = self
                self.Runtime = self
                self.Network = self

            async def attachToTarget(self, params):
                calls['attach_count'] += 1
                calls['attach_params'] = params
                return {'sessionId': 'session-abc'}

            async def enable(self, session_id=None):
                # record enables; append the passed session_id
                calls['enabled_sessions'].append(session_id)
                return {}

        class DummyClient:
            def __init__(self):
                self.send = DummySend()

        class DummyBrowserSession:
            def __init__(self):
                self.cdp_client = DummyClient()
                self.id = 'browser-session-id'

        # Create Page with no initial session_id so _ensure_session runs attach flow
        page = Page(DummyBrowserSession(), target_id='target-1', session_id=None)

        # Use dynamic import to avoid top-level import statements in this test output
        asyncio = __import__('asyncio')

        # Run the coroutine to ensure session is established
        result_session_id = asyncio.run(page._ensure_session())

        # Validate attachToTarget was called exactly once with expected params
        self.assertEqual(calls['attach_count'], 1)
        self.assertEqual(calls['attach_params'], {'targetId': 'target-1', 'flatten': True})

        # Validate returned and stored session id
        self.assertEqual(result_session_id, 'session-abc')
        self.assertEqual(page._session_id, 'session-abc')

        # Validate that all four domains were enabled with the correct session id
        self.assertEqual(len(calls['enabled_sessions']), 4)
        self.assertTrue(all(sid == 'session-abc' for sid in calls['enabled_sessions']))

        # Calling _ensure_session again should not call attachToTarget again
        second_session_id = asyncio.run(page._ensure_session())
        self.assertEqual(second_session_id, 'session-abc')
        self.assertEqual(calls['attach_count'], 1)
