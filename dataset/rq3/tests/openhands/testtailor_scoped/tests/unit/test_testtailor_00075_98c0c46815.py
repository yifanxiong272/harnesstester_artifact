import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.bitbucket_data_center')
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
        """Verify set_owner updates the owner attribute and dynamic URLs reflect the new owner."""
        handler = BitbucketDCIssueHandler(
            owner='PROJ',
            repo='my-repo',
            token='user:secret',
            base_domain='bitbucket.example.com',
        )

        # Sanity check initial state
        self.assertEqual(handler.owner, 'PROJ')
        self.assertEqual(
            handler.get_repo_url(),
            'https://bitbucket.example.com/projects/PROJ/repos/my-repo',
        )

        # Call the method under test
        handler.set_owner('NEWPROJ')

        # The owner attribute should be updated
        self.assertEqual(handler.owner, 'NEWPROJ')

        # Methods that compute URLs dynamically should reflect the new owner
        self.assertEqual(
            handler.get_repo_url(),
            'https://bitbucket.example.com/projects/NEWPROJ/repos/my-repo',
        )
        # get_clone_url uses owner.lower() internally
        self.assertEqual(
            handler.get_clone_url(),
            'https://bitbucket.example.com/scm/newproj/my-repo.git',
        )
