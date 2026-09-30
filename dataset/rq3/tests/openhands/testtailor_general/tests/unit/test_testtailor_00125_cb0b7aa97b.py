import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.github')
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
        """Ensure get_base_url returns GitHub Enterprise API v3 URL when base_domain is not github.com"""
        owner = 'myowner'
        repo = 'myrepo'
        token = 'secrettoken'
        base_domain = 'ghe.example.com'
        handler = GithubIssueHandler(owner, repo, token, username='user', base_domain=base_domain)

        expected = f'https://{base_domain}/api/v3/repos/{owner}/{repo}'
        # get_base_url should produce enterprise-style URL
        self.assertEqual(handler.get_base_url(), expected)
        # __init__ should have set base_url to the same value
        self.assertEqual(handler.base_url, expected)
        # download_url is based on base_url and should include /issues
        self.assertEqual(handler.download_url, expected + '/issues')
