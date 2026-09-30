import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.gitlab.service.branches')
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
        """Verify get_branches builds encoded URL, uses per_page=100 and page=1, and returns Branch objects."""

        # Dummy client implementing the minimal attributes/methods required by the mixin
        class DummyClient(GitLabBranchesMixin):
            BASE_URL = "https://gitlab.example.com/api/v4"

            def __init__(self):
                # capture calls for assertions
                self.calls = []

            # Implement abstract methods from base class with simple stubs
            def _get_cursorrules_url(self, *args, **kwargs):
                return "unused"

            def _get_file_name_from_item(self, *args, **kwargs):
                return "unused"

            def _get_file_path_from_item(self, *args, **kwargs):
                return "unused"

            def _get_microagents_directory_params(self, *args, **kwargs):
                return {}

            def _get_microagents_directory_url(self, *args, **kwargs):
                return "unused"

            def _is_valid_microagent_file(self, *args, **kwargs):
                return True

            async def _make_request(self, url, params):
                # record the call
                self.calls.append((url, params))

                # Simulate a single page response with one branch and no 'next' link
                response = [
                    {
                        "name": "main",
                        "commit": {"id": "abc123", "committed_date": "2020-01-01T00:00:00Z"},
                        "protected": True,
                    }
                ]
                headers = {}  # no Link header -> no next page
                return response, headers

        client = DummyClient()

        # Run the async method without a direct import by using __import__
        loop = __import__("asyncio").get_event_loop()
        branches = loop.run_until_complete(client.get_branches("group/repo"))

        # Assertions on returned Branch objects
        self.assertEqual(len(branches), 1)
        branch = branches[0]
        self.assertEqual(branch.name, "main")
        self.assertEqual(branch.commit_sha, "abc123")
        self.assertTrue(branch.protected)
        self.assertEqual(branch.last_push_date, "2020-01-01T00:00:00Z")

        # Verify the URL was encoded and per_page/page params were used as expected
        self.assertEqual(len(client.calls), 1)
        called_url, called_params = client.calls[0]
        expected_encoded = "group%2Frepo"
        self.assertIn(f"/projects/{expected_encoded}/repository/branches", called_url)
        self.assertEqual(called_params, {"per_page": "100", "page": "1"})
