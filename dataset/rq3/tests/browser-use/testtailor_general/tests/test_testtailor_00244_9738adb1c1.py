import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.mouse')
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
        """Verify Mouse.click dispatches press and release mouse events with correct params."""
        calls = []

        # Create a fake Input with an async dispatchMouseEvent that records calls
        class DummyInput:
            async def dispatchMouseEvent(self, params, session_id=None):
                calls.append((params, session_id))

        # Build a fake client with nested send.Input
        class SendHolder:
            pass

        send_holder = SendHolder()
        send_holder.Input = DummyInput()

        class DummyClient:
            def __init__(self, send):
                self.send = send

        client = DummyClient(send_holder)

        # Fake browser_session holding the client
        class BrowserSession:
            pass

        browser_session = BrowserSession()
        browser_session.cdp_client = client

        # Instantiate Mouse from the module under test
        mouse = Mouse(browser_session, session_id='session-123', target_id=None)

        # Use __import__ to get asyncio without top-level import
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(mouse.click(123, 456, button='right', click_count=2))
        finally:
            try:
                loop.run_until_complete(asyncio.sleep(0))  # allow any pending tasks to settle
            except Exception:
                pass
            loop.close()
            asyncio.set_event_loop(None)

        # Two calls: press then release
        self.assertEqual(len(calls), 2)

        press_params, press_sid = calls[0]
        release_params, release_sid = calls[1]

        self.assertEqual(press_sid, 'session-123')
        self.assertEqual(release_sid, 'session-123')

        expected_press = {
            'type': 'mousePressed',
            'x': 123,
            'y': 456,
            'button': 'right',
            'clickCount': 2,
        }
        expected_release = {
            'type': 'mouseReleased',
            'x': 123,
            'y': 456,
            'button': 'right',
            'clickCount': 2,
        }

        self.assertEqual(press_params, expected_press)
        self.assertEqual(release_params, expected_release)
