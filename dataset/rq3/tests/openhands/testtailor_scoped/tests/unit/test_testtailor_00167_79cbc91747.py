import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.forgejo')
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
        """Verify that set_owner updates owner, base_url and download_url."""
        handler = ForgejoIssueHandler(
            owner='old-owner',
            repo='test-repo',
            token='test-token',
            username='test-user',
            base_domain='example.com',
        )

        # initial state references the original owner
        self.assertEqual(handler.owner, 'old-owner')
        self.assertIn('/repos/old-owner/test-repo', handler.base_url)
        self.assertIn('/issues', handler.download_url)

        # Call the method under test
        handler.set_owner('new-owner')

        # Owner should be updated
        self.assertEqual(handler.owner, 'new-owner')

        # base_url and download_url should have been recomputed to include the new owner
        self.assertEqual(handler.base_url, handler.get_base_url())
        self.assertEqual(handler.download_url, handler.get_download_url())
        self.assertIn('/repos/new-owner/test-repo', handler.base_url)
        self.assertTrue(handler.download_url.endswith('/issues'))
