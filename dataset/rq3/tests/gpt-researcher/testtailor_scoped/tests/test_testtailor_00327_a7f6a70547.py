import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.xquik.xquik')
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
        """Ensure the request URL params and headers are constructed correctly and tweets parsed."""
        # Arrange
        os.environ["XQUIK_API_KEY"] = "testkey"
        query = "hello world"
        search = XquikSearch(query=query)

        # Prepare fake API response
        tweets = [{
            "author": {"username": "alice"},
            "text": "This is a test tweet",
            "id": "123",
            "likeCount": 5,
            "retweetCount": 2,
            "viewCount": 100
        }]
        fake_response = json.dumps({"tweets": tweets}).encode("utf-8")

        with patch("urllib.request.Request") as mock_request, \
             patch("urllib.request.urlopen") as mock_urlopen:
            # urlopen should return a context manager whose __enter__ returns an object with read()
            mock_resp_obj = MagicMock()
            mock_resp_obj.read.return_value = fake_response
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = mock_resp_obj
            mock_cm.__exit__.return_value = None
            mock_urlopen.return_value = mock_cm

            # Act
            results = search._search_tweets(1)

            # Assert: url and headers passed to Request
            expected_params = urllib.parse.urlencode({
                "q": query,
                "limit": 1,
                "queryType": "Top",
            })
            expected_url = f"https://xquik.com/api/v1/x/tweets/search?{expected_params}"
            expected_headers = {
                "X-API-Key": "testkey",
                "Accept": "application/json",
                "User-Agent": "gpt-researcher/1.0",
            }
            mock_request.assert_called_once_with(expected_url, headers=expected_headers)

            # Assert: urlopen called with the Request object and timeout
            mock_urlopen.assert_called_once_with(mock_request.return_value, timeout=15)

            # Assert: results parsed correctly
            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertIn("@alice: This is a test tweet", r["title"])
            self.assertEqual(r["href"], "https://x.com/alice/status/123")
            self.assertIn("5 likes, 2 RTs, 100 views", r["body"])
