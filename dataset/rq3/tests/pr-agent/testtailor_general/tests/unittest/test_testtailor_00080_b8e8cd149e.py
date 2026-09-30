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
        """Ensure ValueError is raised when bitbucket_server_url cannot be parsed and no client is provided."""
        # Backup original method and replace with one that returns empty (falsy) value to trigger the ValueError branch
        original_parse = BitbucketServerProvider._parse_bitbucket_server
        BitbucketServerProvider._parse_bitbucket_server = staticmethod(lambda url: "")
        try:
            with self.assertRaises(ValueError) as ctx:
                BitbucketServerProvider(pr_url="https://git.example.com/projects/AAA/repos/my-repo/pull-requests/1", bitbucket_client=None)
            self.assertIn("Invalid or missing Bitbucket Server URL parsed from PR URL", str(ctx.exception))
        finally:
            # Restore original method
            BitbucketServerProvider._parse_bitbucket_server = original_parse
