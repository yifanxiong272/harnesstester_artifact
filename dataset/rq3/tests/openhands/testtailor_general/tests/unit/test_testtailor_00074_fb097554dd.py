import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.service.base')
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
        """Test BitBucketMixinBase._extract_owner_and_repo splits repository correctly and raises on invalid input."""
        # Create an instance without running any base initializers since the method is stateless
        mixin = object.__new__(BitBucketMixinBase)

        # Normal two-part repository
        owner, repo = mixin._extract_owner_and_repo('workspace/repo_slug')
        self.assertEqual(owner, 'workspace')
        self.assertEqual(repo, 'repo_slug')

        # Repository with more than two segments -> should return the last two segments
        owner2, repo2 = mixin._extract_owner_and_repo('org/team/repo')
        self.assertEqual((owner2, repo2), ('team', 'repo'))

        # Leading empty segment (e.g., '/repo') is allowed by the implementation
        owner3, repo3 = mixin._extract_owner_and_repo('/repo')
        self.assertEqual((owner3, repo3), ('', 'repo'))

        # Invalid repository (no slash) should raise ValueError
        with self.assertRaises(ValueError) as cm:
            mixin._extract_owner_and_repo('invalidrepo')
        self.assertIn('Invalid repository name', str(cm.exception))
