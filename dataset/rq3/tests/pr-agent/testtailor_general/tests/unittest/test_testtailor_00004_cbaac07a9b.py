import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_similar_issue')
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
        """Verify PRSimilarIssue __init__ sets core attributes when provider is GitHub and vectordb is non-matching."""
        # Local imports so we don't add global import statements
        import pr_agent.tools.pr_similar_issue as module

        # Prepare fake settings to exercise target path
        class FakeSettings:
            class config:
                git_provider = "github"
                publish_output = False

            class CONFIG:
                CLI_MODE = True

            class pr_similar_issue:
                max_issues_to_scan = 50
                vectordb = "none"  # not pinecone/lancedb/qdrant so constructor stops after index_name assignment
                force_update_dataset = False
                skip_comments = True

        # Fake TokenHandler to avoid external dependencies during init
        class FakeTokenHandler:
            def __init__(self, *args, **kwargs):
                pass

        # Fake repository object returned by github_client.get_repo
        class FakeRepo:
            def __init__(self, full_name="Owner/Repo"):
                self.full_name = full_name

        # Fake github client with get_repo
        class FakeGithubClient:
            def get_repo(self, repo_name):
                return FakeRepo(full_name=repo_name)

        # Fake git provider class returned by get_git_provider()
        class FakeGitProvider:
            def __init__(self):
                self.github_client = FakeGithubClient()
                self.repo = None
                self.repo_obj = None

            def _parse_issue_url(self, part):
                # Return repo name and dummy issue number
                return ("owner/repo", 1)

        # Patch module-level dependencies
        setattr(module, "get_settings", lambda *args, **kwargs: FakeSettings())
        setattr(module, "get_git_provider", lambda *args, **kwargs: FakeGitProvider)
        setattr(module, "TokenHandler", FakeTokenHandler)

        # Now instantiate the tool which should run through target code
        ToolClass = module.PRSimilarIssue
        tool = ToolClass("https://github.com/owner/repo/issues/1", None)

        # Assertions verifying the target assignments
        self.assertEqual(tool.cli_mode, FakeSettings.CONFIG.CLI_MODE)
        self.assertEqual(tool.max_issues_to_scan, FakeSettings.pr_similar_issue.max_issues_to_scan)
        # git_provider should have been instantiated and repo set
        self.assertIsNotNone(tool.git_provider)
        self.assertEqual(tool.git_provider.repo, "owner/repo")
        # repo_obj should be set to the FakeRepo returned by FakeGithubClient.get_repo
        self.assertIsNotNone(tool.git_provider.repo_obj)
        self.assertEqual(tool.git_provider.repo_obj.full_name, "owner/repo")
        # repo_name_for_index should be normalized: lower + '/' -> '-'
        self.assertEqual(tool.repo_name_for_index, "owner-repo")
        # index name constant
        self.assertEqual(tool.index_name, "codium-ai-pr-agent-issues")
        # token_handler should be our fake
        self.assertIsInstance(tool.token_handler, FakeTokenHandler)
