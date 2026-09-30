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
        """set_owner should update the owner attribute and affect methods that use it."""
        handler = BitbucketDCIssueHandler(
            owner='PROJ',
            repo='my-repo',
            token='user:secret',
            base_domain='bitbucket.example.com',
        )

        # initial sanity check
        self.assertEqual(handler.owner, 'PROJ')

        # call the method under test
        handler.set_owner('NEWPROJ')

        # owner attribute should be updated
        self.assertEqual(handler.owner, 'NEWPROJ')

        # methods that build URLs/strings from owner should reflect the new owner
        self.assertEqual(
            handler.get_repo_url(),
            'https://bitbucket.example.com/projects/NEWPROJ/repos/my-repo',
        )
        self.assertEqual(
            handler.get_download_url(),
            'https://bitbucket.example.com/rest/api/latest/projects/NEWPROJ/repos/my-repo/archive?format=zip',
        )
        # clone_url uses lowercased owner in its construction
        self.assertEqual(
            handler.get_clone_url(),
            'https://bitbucket.example.com/scm/newproj/my-repo.git',
        )
        # branch name builder should include the new owner
        self.assertEqual(handler.get_branch_name('feature/x'), 'feature/x-NEWPROJ')
