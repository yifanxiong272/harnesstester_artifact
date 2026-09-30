import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serper.serper')
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
        """Test SerperSearch __init__ uses provided args and environment fallbacks correctly."""
        # Preserve original environment to restore later
        orig_env = {
            "SERPER_REGION": os.environ.get("SERPER_REGION"),
            "SERPER_LANGUAGE": os.environ.get("SERPER_LANGUAGE"),
            "SERPER_TIME_RANGE": os.environ.get("SERPER_TIME_RANGE"),
            "SERPER_EXCLUDE_SITES": os.environ.get("SERPER_EXCLUDE_SITES"),
            "SERPER_API_KEY": os.environ.get("SERPER_API_KEY"),
        }
        try:
            # Set environment variables for defaults
            os.environ["SERPER_REGION"] = "us"
            os.environ["SERPER_LANGUAGE"] = "en"
            os.environ["SERPER_TIME_RANGE"] = "qdr:d"
            os.environ["SERPER_EXCLUDE_SITES"] = "example.com, test.com"
            os.environ["SERPER_API_KEY"] = "fake_api_key_123"

            # Case A: rely on environment for country/language/time_range/exclude_sites/api_key
            s = SerperSearch(query="hello world")
            self.assertEqual(s.query, "hello world")
            self.assertIsNone(s.query_domains)
            self.assertEqual(s.country, "us")
            self.assertEqual(s.language, "en")
            self.assertEqual(s.time_range, "qdr:d")
            # exclude_sites should be parsed into a list with whitespace stripped
            self.assertEqual(s.exclude_sites, ["example.com", "test.com"])
            self.assertEqual(s.api_key, "fake_api_key_123")

            # Case B: provide explicit parameters to override environment defaults
            explicit_excludes = ["override.com"]
            explicit_domains = ["a.com", "b.com"]
            s2 = SerperSearch(
                query="another query",
                query_domains=explicit_domains,
                country="kr",
                language="ko",
                time_range="qdr:w",
                exclude_sites=explicit_excludes
            )
            self.assertEqual(s2.query, "another query")
            self.assertEqual(s2.query_domains, explicit_domains)
            self.assertEqual(s2.country, "kr")
            self.assertEqual(s2.language, "ko")
            self.assertEqual(s2.time_range, "qdr:w")
            self.assertEqual(s2.exclude_sites, explicit_excludes)
            self.assertEqual(s2.api_key, "fake_api_key_123")
        finally:
            # Restore original environment
            for k, v in orig_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
