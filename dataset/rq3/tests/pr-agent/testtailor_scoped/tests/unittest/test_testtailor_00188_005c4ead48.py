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
        # Ensure set_pr assigns self.pr by calling _get_pr() after parsing the URL
        with patch.object(CodeCommitProvider, "__init__", lambda self, pr_url=None, incremental=False: None):
            provider = CodeCommitProvider(None)

            # Prepare a mimic PR object to be returned by _get_pr
            mimic = PullRequestCCMimic("Mimic Title", [])

            with patch.object(CodeCommitProvider, "_get_pr", return_value=mimic) as mock_get_pr:
                url = "https://us-east-1.console.aws.amazon.com/codesuite/codecommit/repositories/test_repo/pull-requests/987"
                provider.set_pr(url)

                # _get_pr should have been called and its return assigned to provider.pr
                mock_get_pr.assert_called_once()
                self.assertEqual(provider.repo_name, "test_repo")
                self.assertEqual(provider.pr_num, 987)
                self.assertIs(provider.pr, mimic)
