import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.local_git_provider')
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
        """Verify PullRequestMimic stores title and diff_files reference correctly."""
        # prepare two FilePatchInfo instances using the required constructor signature
        f1 = FilePatchInfo("a_base.txt", "a_head.txt", "+Hello\n", "a.txt")
        f1.tokens = 10

        f2 = FilePatchInfo("b_base.txt", "b_head.txt", "-World\n", "b.txt")
        f2.tokens = 5

        diff_list = [f1, f2]
        title = "Test PR Title"

        # construct the PullRequestMimic under test
        pr = PullRequestMimic(title=title, diff_files=diff_list)

        # assertions: title preserved, diff_files reference preserved, contents intact
        self.assertEqual(pr.title, title)
        self.assertIs(pr.diff_files, diff_list)
        self.assertEqual(len(pr.diff_files), 2)
        self.assertIs(pr.diff_files[0], f1)
        self.assertIs(pr.diff_files[1], f2)
        self.assertEqual(pr.diff_files[0].filename, "a.txt")
        self.assertEqual(pr.diff_files[1].patch, "-World\n")
        self.assertEqual(pr.diff_files[0].tokens, 10)
