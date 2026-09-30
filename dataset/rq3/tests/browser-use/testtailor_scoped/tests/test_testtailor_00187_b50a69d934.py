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
        """Ensure Page.session_id calls _ensure_session and caches the session id,
        and that the necessary domain enable calls are made with the returned session id.
        """
        async def run_test():
            # trackers for calls
            attach_calls = []
            page_enable_calls = []
            dom_enable_calls = []
            runtime_enable_calls = []
            network_enable_calls = []

            # create simple service implementations
            class TargetService:
                async def attachToTarget(self, params):
                    attach_calls.append(params)
                    return {'sessionId': 'sess-123'}

            class PageService:
                async def enable(self, session_id=None):
                    page_enable_calls.append(session_id)

            class DOMService:
                async def enable(self, session_id=None):
                    dom_enable_calls.append(session_id)

            class RuntimeService:
                async def enable(self, session_id=None):
                    runtime_enable_calls.append(session_id)

            class NetworkService:
                async def enable(self, session_id=None):
                    network_enable_calls.append(session_id)

            # assemble send tree
            class Send:
                pass

            send = Send()
            send.Target = TargetService()
            send.Page = PageService()
            send.DOM = DOMService()
            send.Runtime = RuntimeService()
            send.Network = NetworkService()

            # cdp client and browser session mocks
            class CdpClient:
                pass

            cdp_client = CdpClient()
            cdp_client.send = send

            class BrowserSession:
                pass

            browser_session = BrowserSession()
            browser_session.cdp_client = cdp_client
            browser_session.id = 'bs-1'

            # Create Page instance under test
            page = Page(browser_session, 'target-1')

            # First access should call attachToTarget and enable calls
            sid = await page.session_id
            self.assertEqual(sid, 'sess-123')

            self.assertEqual(len(attach_calls), 1)
            self.assertEqual(attach_calls[0], {'targetId': 'target-1', 'flatten': True})

            self.assertEqual(page_enable_calls, ['sess-123'])
            self.assertEqual(dom_enable_calls, ['sess-123'])
            self.assertEqual(runtime_enable_calls, ['sess-123'])
            self.assertEqual(network_enable_calls, ['sess-123'])

            # Second access should use cached session id and not call attach again
            sid2 = await page.session_id
            self.assertEqual(sid2, 'sess-123')

            # attach should still have been awaited only once
            self.assertEqual(len(attach_calls), 1)

        # run the async test without top-level import
        __import__('asyncio').run(run_test())
