import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.action_execution_server')
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
        verify = globals().get('verify_api_key')
        self.assertIsNotNone(verify, "verify_api_key not found in globals")

        # Set the module-level SESSION_API_KEY so the function checks it
        verify.__globals__['SESSION_API_KEY'] = 'expected-session-key'

        HTTPException = verify.__globals__['HTTPException']

        # Handle both sync and async function variants
        import inspect, asyncio

        if inspect.iscoroutinefunction(verify):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If an event loop is already running in the test environment, skip to avoid deadlock
                self.skipTest("Event loop is already running; cannot run coroutine synchronously in this environment")
            else:
                with self.assertRaises(HTTPException) as cm:
                    asyncio.run(verify(api_key='wrong-key'))
        else:
            with self.assertRaises(HTTPException) as cm:
                verify(api_key='wrong-key')

        exc = cm.exception
        self.assertEqual(getattr(exc, 'status_code', None), 403)
        self.assertEqual(getattr(exc, 'detail', None), 'Invalid API Key')
