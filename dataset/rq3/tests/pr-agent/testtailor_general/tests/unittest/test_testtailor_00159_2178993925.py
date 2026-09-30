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
        """Ensure AI metadata is added to diff files when is_auto_command and enable_ai_metadata are enabled."""
        settings = get_settings()
        orig_is_auto = settings.get("config.is_auto_command", False)
        orig_enable_ai = settings.get("config.enable_ai_metadata", False)
        try:
            # Enable the flags that trigger the add_ai_metadata_to_diff_files branch
            settings.set("config.is_auto_command", True)
            settings.set("config.enable_ai_metadata", True)

            # Minimal dummy AI handler class (PRReviewer will instantiate it)
            class DummyAIHandler:
                def __init__(self):
                    # PRReviewer sets main_pr_language on the handler; allow that.
                    self.main_pr_language = None

                async def chat_completion(self, *args, **kwargs):
                    return "", "stop"

            # Dummy PR and File classes to simulate a git provider
            class DummyPR:
                title = "dummy pr title"

            class DummyFile:
                def __init__(self, filename):
                    self.filename = filename
                    self.ai_file_summary = None

            class DummyGitProvider:
                def __init__(self, pr_url):
                    self.pr = DummyPR()
                    self._diff_files = [DummyFile("foo.py")]

                def get_incremental_commits(self, incremental):
                    return None

                def get_languages(self):
                    return {"python": 100}

                def get_files(self):
                    return ["foo.py"]

                def is_supported(self, feature):
                    # Keep simple: not used for this branch check but safe to return True
                    return True

                def get_pr_description(self, split_changes_walkthrough=True):
                    # Return a description and pr_description_files matching the diff filename
                    return ("some description", [{"full_file_name": "foo.py", "ai_file_summary": "AI summary"}])

                def get_commit_messages(self):
                    return "commit message"

                def get_num_of_files(self):
                    return 1

                def get_pr_branch(self):
                    return "branch"

                def get_diff_files(self):
                    return self._diff_files

            # Patch the get_git_provider_with_context used by PRReviewer to return our dummy provider
            with patch("pr_agent.tools.pr_reviewer.get_git_provider_with_context", return_value=DummyGitProvider("http://example.com/pr/1")):
                # Instantiate PRReviewer which should call add_ai_metadata_to_diff_files during init
                reviewer = PRReviewer("http://example.com/pr/1", is_answer=False, is_auto=True, args=None, ai_handler=DummyAIHandler)

                # After initialization, the dummy diff file should have received ai_file_summary from pr_description_files
                diff_files = reviewer.git_provider.get_diff_files()
                self.assertTrue(len(diff_files) > 0, "No diff files returned from dummy git provider")
                # The ai_file_summary should be set to the matching pr_description_files entry
                self.assertIsNotNone(getattr(diff_files[0], "ai_file_summary", None), "AI metadata was not added to the diff file")
        finally:
            # Restore original settings
            settings.set("config.is_auto_command", orig_is_auto)
            settings.set("config.enable_ai_metadata", orig_enable_ai)
