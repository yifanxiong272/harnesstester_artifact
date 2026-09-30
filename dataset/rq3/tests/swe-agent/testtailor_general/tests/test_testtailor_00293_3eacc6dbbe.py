import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.open_pr')
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
        """Ensure open_pr calls the GitHub API to create a PR when not a dry run."""
        # Arrange
        mock_logger = unittest.mock.Mock()

        class FakeEnv:
            def communicate(self, input: str, timeout: int = 25, *, check: str = "ignore", error_msg: str = "Command failed"):
                # Simulate successful command execution for any git operations
                return "ok"

        env = FakeEnv()

        # Fake issue data returned by _get_gh_issue_data
        fake_issue = unittest.mock.Mock()
        fake_issue.number = 1
        fake_issue.title = "Fix something"

        # Fake GhApi and its pulls.create return value
        fake_api_instance = unittest.mock.Mock()
        fake_pr = unittest.mock.Mock()
        fake_pr.html_url = "https://github.com/owner/repo/pull/1"
        fake_api_instance.pulls.create.return_value = fake_pr

        # Patch dependencies in the module under test
        with unittest.mock.patch("sweagent.run.hooks.open_pr._get_gh_issue_data", return_value=fake_issue) as mocked_get_issue, \
             unittest.mock.patch("sweagent.run.hooks.open_pr._parse_gh_issue_url", return_value=("owner", "repo", "1")) as mocked_parse, \
             unittest.mock.patch("sweagent.run.hooks.open_pr.GhApi", return_value=fake_api_instance) as mocked_ghapi:

            # Act
            open_pr(
                logger=mock_logger,
                token="fake-token",
                env=env,
                github_url="https://github.com/owner/repo/issues/1",
                trajectory=[{"response": "resp", "observation": "obs"}],
                _dry_run=False,
            )

            # Assert API was constructed and create was called with expected args
            mocked_ghapi.assert_called_once_with(token="fake-token")
            fake_api_instance.pulls.create.assert_called_once()
            create_kwargs = fake_api_instance.pulls.create.call_args.kwargs
            self.assertEqual(create_kwargs["owner"], "owner")
            self.assertEqual(create_kwargs["repo"], "repo")
            self.assertIn("Fix something", create_kwargs["title"])
            self.assertEqual(create_kwargs["base"], "main")
            self.assertTrue(create_kwargs["draft"])

            # Assert logger was informed about the created PR and contains the PR url
            self.assertTrue(mock_logger.info.called)
            info_call_args = mock_logger.info.call_args[0][0]
            self.assertIn(fake_pr.html_url, info_call_args)
