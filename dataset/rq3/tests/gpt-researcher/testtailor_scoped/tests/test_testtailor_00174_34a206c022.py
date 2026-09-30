import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.tavily.tavily_search')
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
        """Ensure get_api_key returns empty string and prints message when TAVILY_API_KEY is missing."""
        # Clear environment to simulate missing TAVILY_API_KEY
        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.print") as mock_print:
                # Instantiate TavilySearch which calls get_api_key in __init__
                ts = TavilySearch(query="test query")
                # api_key should be set to empty string when environment variable is missing
                self.assertEqual(ts.api_key, "")
                # Ensure the expected message was printed
                mock_print.assert_called_once_with(
                    "Tavily API key not found, set to blank. If you need a retriver, please set the TAVILY_API_KEY environment variable."
                )
