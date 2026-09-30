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
        """Ensure commit message is prefixed with 'aider: ' when commit message prefixing is enabled."""
        # Create a GitRepo-like object without initializing a real git repo on disk.
        grepo = GitRepo.__new__(GitRepo)

        # Provide a simple get_diffs implementation so commit() proceeds.
        grepo.get_diffs = lambda fnames: "diff -- example"

        # abs_root_path should return the path unchanged for our fake repo.
        grepo.abs_root_path = lambda p: p

        # Minimal fake git layer to satisfy calls to repo.git.add, repo.git.commit, and repo.git.config
        class _FakeGit:
            def add(self, fname):
                # simulate successful add
                return None

            def commit(self, cmd):
                # simulate successful commit
                return None

            def config(self, *args):
                # mimic `git config --get user.name`
                return "Test User"

        class _FakeRepo:
            def __init__(self):
                self.git = _FakeGit()

        grepo.repo = _FakeRepo()

        # Provide get_head_commit_sha and get_head_commit_message for post-commit checks
        grepo.get_head_commit_sha = lambda short=True: "deadbee"[:7]
        grepo.get_head_commit_message = lambda default=None: "aider: My message"

        # Provide simple io object to capture outputs without raising
        class _IO:
            def __init__(self):
                self.last_output = None
                self.last_error = None

            def tool_output(self, msg, bold=False):
                self.last_output = msg

            def tool_error(self, msg):
                self.last_error = msg

        grepo.io = _IO()

        # Ensure we do NOT trigger author/committer env changes by disabling those attributes.
        grepo.attribute_author = False
        grepo.attribute_committer = False

        # Enable commit-message prefixing for author side so prefix_commit_message becomes True
        grepo.attribute_commit_message_author = True
        grepo.attribute_commit_message_committer = False

        # Ensure co-authored-by is False so prefixing logic applies as expected
        grepo.attribute_co_authored_by = False

        # Keep git_commit_verify default True so no --no-verify handling required
        grepo.git_commit_verify = True

        # Now call commit with a filename list and explicit message and aider_edits=True
        result = grepo.commit(fnames=["file.txt"], message="My message", aider_edits=True, coder=None)

        # Should have returned a (hash, message) tuple
        self.assertIsNotNone(result)
        commit_hash, returned_message = result

        # Verify commit hash and message are as expected/present
        self.assertEqual(commit_hash, "deadbee"[:7])
        self.assertEqual(returned_message, "aider: My message")

        # Also verify that the fake repo's reported head commit message includes the prefix
        self.assertTrue(grepo.get_head_commit_message().startswith("aider: My message"))
