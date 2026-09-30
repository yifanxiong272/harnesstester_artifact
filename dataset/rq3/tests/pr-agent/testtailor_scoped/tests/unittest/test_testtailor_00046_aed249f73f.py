import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.github_provider')
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
        """Ensure __init__ processes a PR URL: set_pr is called, pr_commits and last_commit_id and pr_url set."""
        # Prepare mocks
        mock_client = MagicMock()
        mock_repo_obj = MagicMock()
        mock_pr = MagicMock()

        # Configure the client -> repo -> pull behavior
        mock_client.get_repo.return_value = mock_repo_obj
        mock_repo_obj.get_pull.return_value = mock_pr

        # Configure a PR URL that will be parsed by _parse_pr_url
        pr_url = "https://github.com/example_owner/example_repo/pull/42"

        # Prepare commits returned by get_commits()
        commit1 = MagicMock()
        commit2 = MagicMock()
        # make commits identifiable
        commit1.commit = MagicMock()
        commit1.commit.message = "first commit"
        commit2.commit = MagicMock()
        commit2.commit.message = "second commit"
        mock_pr.get_commits.return_value = [commit1, commit2]

        # Provide pr html_url used by get_pr_url()
        mock_pr.html_url = "https://github.com/example_owner/example_repo/pull/42"

        # Patch the provider to return our mock client when creating the GitHub client
        with patch.object(GithubProvider, "_get_github_client", return_value=mock_client):
            provider = GithubProvider(pr_url=pr_url)

        # Assertions: set_pr should have parsed repo and number
        self.assertEqual(provider.repo, "example_owner/example_repo")
        self.assertEqual(provider.pr_num, 42)
        # pr should be the mock PR and commits should be the list we provided
        self.assertIs(provider.pr, mock_pr)
        self.assertEqual(provider.pr_commits, [commit1, commit2])
        # last_commit_id should be the last commit in the list
        self.assertIs(provider.last_commit_id, commit2)
        # pr_url stored should come from the PR object's html_url via get_pr_url()
        self.assertEqual(provider.pr_url, mock_pr.html_url)
