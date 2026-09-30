import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_reviewer')
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
        """Ensure that when args contains '-i' (incremental), PRReviewer calls
        git_provider.get_incremental_commits with the incremental object."""
        # Set up a fake PR and fake GitProvider that records calls to get_incremental_commits
        called = {}

        class FakePR:
            title = "Fake PR Title"

        class FakeGitProvider:
            def __init__(self, pr_url):
                self.pr = FakePR()
                self.pr_url = pr_url
                self.get_incremental_commits_called = False
                self.get_incremental_commits_arg = None

            def get_incremental_commits(self, incremental):
                # record that this method was invoked and with which object
                self.get_incremental_commits_called = True
                self.get_incremental_commits_arg = incremental

            # minimal methods used during PRReviewer.__init__
            def get_languages(self):
                return {"python": 10}

            def get_files(self):
                return ["foo.py"]

            def get_pr_description(self, split_changes_walkthrough=True):
                return ("fake description", [])

            def is_supported(self, feature):
                # Keep features simple/available for init
                return True

            def get_commit_messages(self):
                return "commit message"

            def get_num_of_files(self):
                return 1

            def get_pr_branch(self):
                return "branch-name"

            def get_diff_files(self):
                return []

            def get_pr_url(self):
                return self.pr_url

            def get_pr_labels(self, update=False):
                return []

        # Simple dummy AI handler to avoid heavy real initialization
        class DummyAIHandler:
            def __init__(self):
                self.main_pr_language = None

            async def chat_completion(self, *args, **kwargs):
                return "", "stop"

        # Patch the provider factory mapping so get_git_provider_with_context constructs our FakeGitProvider
        provider_id = get_settings().config.git_provider
        with patch.dict('pr_agent.git_providers._GIT_PROVIDERS', {provider_id: FakeGitProvider}, clear=False):
            pr_url = "http://example.com/fake/pr/1"
            # Instantiate PRReviewer with '-i' so incremental.is_incremental is True
            reviewer = PRReviewer(pr_url, args=["-i"], ai_handler=DummyAIHandler)

            # The fake provider instance should be the git_provider used by the reviewer
            self.assertIsInstance(reviewer.git_provider, FakeGitProvider)

            # Incremental flag should be set on the reviewer
            self.assertTrue(reviewer.incremental.is_incremental)

            # And get_incremental_commits should have been called during __init__
            self.assertTrue(reviewer.git_provider.get_incremental_commits_called,
                            "get_incremental_commits was not called for incremental review")
            # The argument passed should be the same incremental object stored on reviewer
            self.assertIs(reviewer.git_provider.get_incremental_commits_arg, reviewer.incremental)
