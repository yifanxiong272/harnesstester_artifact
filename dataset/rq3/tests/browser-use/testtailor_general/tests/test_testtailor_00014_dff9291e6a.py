import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.element')
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
        """Verify Element.__init__ stores provided browser_session, cdp_client, backend_node_id, and session_id."""
        # Minimal dummy browser session to provide a cdp_client attribute
        class DummyBrowserSession:
            def __init__(self, client):
                self.cdp_client = client

        dummy_client = object()
        browser_session = DummyBrowserSession(dummy_client)
        backend_node_id = 42
        session_id = "session-abc"

        # Instantiate Element and verify internals
        element = Element(browser_session, backend_node_id, session_id)

        self.assertIs(element._browser_session, browser_session, "_browser_session should reference the provided BrowserSession")
        self.assertIs(element._client, dummy_client, "_client should reference browser_session.cdp_client")
        self.assertEqual(element._backend_node_id, backend_node_id, "_backend_node_id should match provided value")
        self.assertEqual(element._session_id, session_id, "_session_id should match provided value")

        # Also verify behavior when session_id is None
        element_none = Element(browser_session, backend_node_id, None)
        self.assertIs(element_none._browser_session, browser_session)
        self.assertIs(element_none._client, dummy_client)
        self.assertEqual(element_none._backend_node_id, backend_node_id)
        self.assertIsNone(element_none._session_id)
