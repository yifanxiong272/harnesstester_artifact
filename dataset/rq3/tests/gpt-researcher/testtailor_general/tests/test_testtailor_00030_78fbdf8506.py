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
        """Test SerperSearch __init__ uses passed values and falls back to environment variables."""
        # Preserve existing env to restore later
        old_env = {k: os.environ.get(k) for k in ("SERPER_REGION", "SERPER_LANGUAGE", "SERPER_TIME_RANGE", "SERPER_EXCLUDE_SITES", "SERPER_API_KEY")}
        try:
            # Set environment variables that should be picked up when parameters are None
            os.environ["SERPER_REGION"] = "us"
            os.environ["SERPER_LANGUAGE"] = "en"
            os.environ["SERPER_TIME_RANGE"] = "qdr:m"
            os.environ["SERPER_EXCLUDE_SITES"] = "example.com, test.org"
            os.environ["SERPER_API_KEY"] = "fakekey123"

            # Create instance providing only query and query_domains to cause other fields to be read from env
            s = SerperSearch("my query", query_domains=["a.com", "b.com"])

            # Verify initialization took parameters and environment fallbacks correctly
            self.assertEqual(s.query, "my query")
            self.assertEqual(s.query_domains, ["a.com", "b.com"])
            self.assertEqual(s.country, "us")
            self.assertEqual(s.language, "en")
            self.assertEqual(s.time_range, "qdr:m")
            self.assertEqual(s.exclude_sites, ["example.com", "test.org"])
            self.assertEqual(s.api_key, "fakekey123")

            # Now verify explicit parameters override environment values
            s2 = SerperSearch("other", query_domains=None, country="kr", language="ko", time_range="qdr:d", exclude_sites=["override.com"])
            self.assertEqual(s2.query, "other")
            self.assertIsNone(s2.query_domains)
            self.assertEqual(s2.country, "kr")
            self.assertEqual(s2.language, "ko")
            self.assertEqual(s2.time_range, "qdr:d")
            self.assertEqual(s2.exclude_sites, ["override.com"])
            self.assertEqual(s2.api_key, "fakekey123")
        finally:
            # Restore previous environment
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
