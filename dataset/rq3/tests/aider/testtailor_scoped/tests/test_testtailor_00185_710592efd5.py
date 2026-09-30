import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repo')
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
        """When git.add raises a git error, commit should record the add error via io.tool_error
        and still proceed to call git.commit, returning the commit hash and message."""
        # Create a GitRepo instance without running __init__
        git_repo = object.__new__(GitRepo)

        # Mock IO to capture tool_error/tool_output calls
        git_repo.io = MagicMock()
        git_repo.io.tool_error = MagicMock()
        git_repo.io.tool_output = MagicMock()

        # Mock underlying repo.git behavior
        git_repo.repo = MagicMock()
        git_repo.repo.git = MagicMock()

        # Provide a user.name from git config
        git_repo.repo.git.config = MagicMock(return_value="Test User")

        # Make git.add raise a GitCommandError to trigger the except branch
        def fake_add(fname):
            raise git.GitCommandError("git add", 1, "fatal add error")

        git_repo.repo.git.add = fake_add

        # Make git.commit a MagicMock so commit proceeds
        git_repo.repo.git.commit = MagicMock(return_value=None)

        # Provide get_diffs to return a non-empty diff so commit continues
        git_repo.get_diffs = MagicMock(return_value="some diff")

        # abs_root_path should return the same filename for simplicity
        git_repo.abs_root_path = lambda p: p

        # Ensure get_head_commit_sha returns a predictable hash
        git_repo.get_head_commit_sha = MagicMock(return_value="deadbeef")

        # Set attribution/config attributes used by commit()
        git_repo.attribute_author = False
        git_repo.attribute_committer = False
        git_repo.attribute_commit_message_author = False
        git_repo.attribute_commit_message_committer = False
        git_repo.attribute_co_authored_by = False

        # Ensure we don't try to bypass verify (keep True)
        git_repo.git_commit_verify = True

        # Call commit with a single filename and an explicit message to avoid model calls
        result = git_repo.commit(fnames=["file.txt"], message="commit message")

        # Assert that the add failure was reported via io.tool_error
        self.assertTrue(git_repo.io.tool_error.called, "Expected tool_error to be called on add failure")
        err_msg = git_repo.io.tool_error.call_args[0][0]
        self.assertIn("Unable to add", err_msg)
        self.assertIn("file.txt", err_msg)

        # Assert git.commit was still invoked
        self.assertTrue(git_repo.repo.git.commit.called, "Expected git.commit to be called despite add failure")
        # Verify commit was called with the expected command list
        expected_cmd = ["-m", "commit message", "--", "file.txt"]
        git_repo.repo.git.commit.assert_called_once_with(expected_cmd)

        # Assert commit returned the expected hash and message
        self.assertEqual(result, ("deadbeef", "commit message"))
