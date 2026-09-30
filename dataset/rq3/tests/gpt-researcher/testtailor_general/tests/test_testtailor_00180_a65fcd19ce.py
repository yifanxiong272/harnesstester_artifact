import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bocha.bocha')
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
        """Test that BoChaSearch.search calls the BoCha API and parses results correctly."""
        # Ensure API key available for BoChaSearch initialization
        os.environ["BOCHA_API_KEY"] = "testkey"

        # Prepare mocked JSON response from the BoCha API
        mocked_json = {
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "Test Title",
                            "url": "http://example.com",
                            "snippet": "This is a test snippet."
                        }
                    ]
                }
            }
        }

        # Patch requests.post to return the mocked response
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = mocked_json
            mock_post.return_value = mock_response

            # Instantiate and call the search method
            searcher = BoChaSearch(query="sample query")
            results = searcher.search(max_results=3)

            # Verify parsed results
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Test Title")
            self.assertEqual(results[0]["href"], "http://example.com")
            self.assertEqual(results[0]["body"], "This is a test snippet.")

            # Verify the correct API call was made
            expected_url = 'https://api.bochaai.com/v1/web-search'
            expected_headers = {
                'Authorization': f'Bearer {os.environ["BOCHA_API_KEY"]}',
                'Content-Type': 'application/json'
            }
            expected_json = {
                "query": "sample query",
                "freshness": "noLimit",
                "summary": True,
                "count": 3
            }
            mock_post.assert_called_once_with(expected_url, headers=expected_headers, json=expected_json)
