import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_server_provider')
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
        """Ensure that a missing/invalid Bitbucket Server URL causes a ValueError in __init__."""
        # Preserve original staticmethod so we can restore it after the test
        original = BitbucketServerProvider.__dict__['_parse_bitbucket_server']
        try:
            # Force _parse_bitbucket_server to return None to trigger the ValueError branch
            BitbucketServerProvider._parse_bitbucket_server = staticmethod(lambda url: None)

            with self.assertRaises(ValueError) as cm:
                # Do not provide a bitbucket_client so the constructor will call our patched parser
                BitbucketServerProvider(pr_url="https://example.invalid/projects/AAA/repos/my-repo/pull-requests/1")

            self.assertIn("Invalid or missing Bitbucket Server URL parsed from PR URL", str(cm.exception))
        finally:
            # Restore original method
            BitbucketServerProvider._parse_bitbucket_server = original
