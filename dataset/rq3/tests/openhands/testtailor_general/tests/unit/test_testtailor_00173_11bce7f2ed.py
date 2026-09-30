import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.service.branches')
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
        class Dummy(BitBucketBranchesMixin):
            BASE_URL = 'https://api.bitbucket.org/2.0'

            def __init__(self):
                self._fetch_called = False
                self._fetch_args = None

            def _extract_owner_and_repo(self, repository: str):
                # Simulate extraction from "owner/repo"
                return ('alice', 'myrepo')

            async def _fetch_paginated_data(self, url, params, max_items):
                # Capture the call for assertions and return fake branch data
                self._fetch_called = True
                self._fetch_args = (url, params, max_items)
                return [
                    {
                        'name': 'main',
                        'target': {'hash': 'abcd1234', 'date': '2022-01-01T12:00:00Z'},
                    },
                    {
                        'name': 'feature',
                        'target': {'hash': 'efgh5678', 'date': '2022-02-01T12:00:00Z'},
                    },
                ]

        dummy = Dummy()
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            branches = loop.run_until_complete(dummy.get_branches('alice/myrepo'))
        finally:
            asyncio.set_event_loop(None)
            loop.close()

        # Ensure pagination fetch was called with expected arguments
        self.assertTrue(dummy._fetch_called)
        url, params, max_items = dummy._fetch_args
        self.assertIn('/repositories/alice/myrepo/refs/branches', url)
        self.assertEqual(params['pagelen'], 100)
        self.assertEqual(params['sort'], '-target.date')
        self.assertEqual(max_items, 1000)

        # Validate returned Branch objects
        self.assertEqual(len(branches), 2)

        b0 = branches[0]
        self.assertEqual(b0.name, 'main')
        self.assertEqual(b0.commit_sha, 'abcd1234')
        self.assertFalse(b0.protected)
        self.assertEqual(b0.last_push_date, '2022-01-01T12:00:00Z')

        b1 = branches[1]
        self.assertEqual(b1.name, 'feature')
        self.assertEqual(b1.commit_sha, 'efgh5678')
        self.assertFalse(b1.protected)
        self.assertEqual(b1.last_push_date, '2022-02-01T12:00:00Z')
