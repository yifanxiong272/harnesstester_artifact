import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.codecommit_provider')
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
        """Verify is_supported returns False for known unsupported capabilities and True otherwise."""
        with patch.object(CodeCommitProvider, "__init__", lambda self, pr_url=None, incremental=False: None):
            provider = CodeCommitProvider()
            unsupported = [
                "get_issue_comments",
                "create_inline_comment",
                "publish_inline_comments",
                "get_labels",
                "gfm_markdown",
            ]
            for cap in unsupported:
                self.assertFalse(provider.is_supported(cap), f"Capability '{cap}' should be unsupported")

            # A capability not in the unsupported list should be supported
            self.assertTrue(provider.is_supported("publish_comment"))
            # Check case-sensitivity: different casing should be treated as supported
            self.assertTrue(provider.is_supported("Get_Issue_Comments"))
