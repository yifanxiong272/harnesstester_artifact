import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.google.google')
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
    def test_google_search_with_query_domains(self):
        """Ensure that when query_domains is provided the domain-restricted query is built and used in the request"""
        # Setup
        domains = ["example.com", "another.org"]
        query = "test search"
        headers = {"google_api_key": "FAKE_API_KEY", "google_cx_key": "FAKE_CX_KEY"}

        # Create GoogleSearch instance with query_domains so the branch is taken
        gs = GoogleSearch(query=query, headers=headers, query_domains=domains)

        # Prepare a fake requests response
        fake_items = [
            {"title": "Result 1", "link": "https://example.com/page1", "snippet": "Snippet 1"},
            {"title": "Result 2", "link": "https://another.org/page2", "snippet": "Snippet 2"},
        ]
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.text = json.dumps({"items": fake_items})

        # Patch requests.get to return our fake response
        with patch("requests.get") as mock_get:
            mock_get.return_value = fake_response

            results = gs.search(max_results=5)

            # Validate results normalized properly
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["title"], "Result 1")
            self.assertEqual(results[0]["href"], "https://example.com/page1")
            self.assertEqual(results[0]["body"], "Snippet 1")

            # Ensure the constructed query with domain restrictions was included in the requested URL
            called_url = mock_get.call_args[0][0]
            expected_domain_query = " OR ".join([f"site:{d}" for d in domains])
            expected_search_query = f"({expected_domain_query}) {query}"
            self.assertIn(expected_search_query, called_url)
