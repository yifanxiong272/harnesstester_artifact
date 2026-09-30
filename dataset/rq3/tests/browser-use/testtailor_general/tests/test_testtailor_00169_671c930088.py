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
        """Ensure _ensure_session calls attachToTarget and enables domains when session is missing."""
        async def run():
            calls = []

            class TargetNamespace:
                @staticmethod
                async def attachToTarget(params):
                    # record call and return fake session id
                    calls.append(("attach", params))
                    return {"sessionId": "sess-123"}

            class PageNamespace:
                @staticmethod
                async def enable(session_id=None):
                    calls.append(("Page.enable", session_id))

            class DOMNamespace:
                @staticmethod
                async def enable(session_id=None):
                    calls.append(("DOM.enable", session_id))

            class RuntimeNamespace:
                @staticmethod
                async def enable(session_id=None):
                    calls.append(("Runtime.enable", session_id))

            class NetworkNamespace:
                @staticmethod
                async def enable(session_id=None):
                    calls.append(("Network.enable", session_id))

            class FakeSend:
                def __init__(self):
                    self.Target = TargetNamespace
                    self.Page = PageNamespace
                    self.DOM = DOMNamespace
                    self.Runtime = RuntimeNamespace
                    self.Network = NetworkNamespace

            class FakeClient:
                def __init__(self):
                    self.send = FakeSend()

            class FakeBrowserSession:
                def __init__(self):
                    self.cdp_client = FakeClient()
                    self.id = "browser-session-id"

            # Create Page with no session id so _ensure_session takes the attachToTarget branch
            page = Page(FakeBrowserSession(), target_id="target-1", session_id=None)

            # Inject the same fake client (ensures page._client.send.* are our fakes)
            page._client = FakeClient()

            sid = await page._ensure_session()
            return page, sid, calls

        # Run the async test logic without adding import statements by using __import__
        loop = __import__('asyncio').get_event_loop()
        page, sid, calls = loop.run_until_complete(run())

        # Verify session id was returned and stored
        self.assertEqual(sid, "sess-123")
        self.assertEqual(page._session_id, "sess-123")

        # Verify attachToTarget was called with the expected params
        self.assertTrue(any(c[0] == "attach" and c[1] == {"targetId": "target-1", "flatten": True} for c in calls))

        # Verify that all enable calls were made (order is not guaranteed due to asyncio.gather)
        enabled_calls = {c[0] for c in calls if c[0].endswith(".enable")}
        self.assertSetEqual(enabled_calls, {"Page.enable", "DOM.enable", "Runtime.enable", "Network.enable"})
