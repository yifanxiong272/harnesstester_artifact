import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.service.prs')
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
        """Get PR details returns the raw Bitbucket API response"""
        repository = 'alice/project-x'
        pr_number = 42
        expected_pr_data = {'id': pr_number, 'state': 'OPEN', 'title': 'Fix bug'}

        class Dummy(BitBucketPRsMixin):
            pass

        dummy = Dummy()
        dummy.BASE_URL = 'https://api.bitbucket.org/2.0'
        expected_url = f'{dummy.BASE_URL}/repositories/{repository}/pullrequests/{pr_number}'

        async def fake_make_request(url, *args, **kwargs):
            # ensure the mixin constructs the expected URL
            self.assertEqual(url, expected_url)
            return expected_pr_data, {}

        # Attach the fake async request function to the instance
        dummy._make_request = fake_make_request

        # Obtain asyncio module via __import__ to avoid top-level import
        asyncio = __import__('asyncio')

        # Run the coroutine and assert the returned data matches the expected payload
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(dummy.get_pr_details(repository, pr_number))
        finally:
            loop.close()

        self.assertEqual(result, expected_pr_data)
