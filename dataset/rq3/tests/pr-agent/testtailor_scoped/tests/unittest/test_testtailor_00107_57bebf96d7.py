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
        # Ensure is_supported returns False for capabilities that CodeCommit does not support,
        # and True for a capability that is supported.
        with patch.object(CodeCommitProvider, "__init__", lambda self, pr_url=None, incremental=False: None):
            provider = CodeCommitProvider()
            unsupported_caps = [
                "get_issue_comments",
                "create_inline_comment",
                "publish_inline_comments",
                "get_labels",
                "gfm_markdown",
            ]
            for cap in unsupported_caps:
                self.assertFalse(provider.is_supported(cap), f"Capability '{cap}' should be unsupported and return False")
            # sanity check: an unrelated capability should return True
            self.assertTrue(provider.is_supported("publish_description"), "Unlisted capability should return True")
