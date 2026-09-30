import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.commands.browser')
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
        """Ensure _execute_js obtains a CDP session from the browser_session and evaluates JS."""
        # Prepare AsyncMock for the nested Runtime.evaluate call
        evaluate = AsyncMock(return_value={'result': {'value': 42}})

        # Build simple nested objects to mimic cdp_client.send.Runtime.evaluate structure
        class RuntimeObj:
            def __init__(self, evaluate_func):
                self.evaluate = evaluate_func

        class SendObj:
            def __init__(self, runtime):
                self.Runtime = runtime

        class CDPClient:
            def __init__(self, send):
                self.send = send

        class CDPSession:
            def __init__(self, session_id, cdp_client):
                self.session_id = session_id
                self.cdp_client = cdp_client

        runtime = RuntimeObj(evaluate)
        send = SendObj(runtime)
        cdp_client = CDPClient(send)
        cdp_session = CDPSession('sess-id-123', cdp_client)

        # Mock the BrowserSession to return our cdp_session when get_or_create_cdp_session is called
        bs = Mock()
        bs.get_or_create_cdp_session = AsyncMock(return_value=cdp_session)

        # Create a simple session-like object with the browser_session attribute
        class SessionLike:
            def __init__(self, browser_session):
                self.browser_session = browser_session

        session = SessionLike(browser_session=bs)

        # Run the async function and verify results and calls
        result = asyncio.run(_execute_js(session, '1+1'))
        self.assertEqual(result, 42)

        # Verify the browser session was asked for a CDP session with the expected args
        bs.get_or_create_cdp_session.assert_awaited_once_with(target_id=None, focus=False)

        # Verify the Runtime.evaluate was called with the expected parameters including session_id
        evaluate.assert_awaited_once_with(
            params={'expression': '1+1', 'returnByValue': True},
            session_id='sess-id-123'
        )
