import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.codecommit_client')
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
        """Ensure is_supported returns False for 'gfm_markdown' and True for other capabilities"""
        client = CodeCommitClient()
        # target branch: capability in ['gfm_markdown'] -> should return False
        self.assertFalse(client.is_supported("gfm_markdown"))
        # sanity check: other capabilities should be supported (True)
        self.assertTrue(client.is_supported("some_other_capability"))
