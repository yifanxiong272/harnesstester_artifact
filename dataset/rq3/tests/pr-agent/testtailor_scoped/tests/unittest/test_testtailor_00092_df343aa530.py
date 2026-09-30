import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.azuredevops_provider')
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
        """Test that publish_code_suggestions initializes parameters and calls create_thread with correct args."""
        # Dummy azure devops client to capture create_thread calls
        calls = []

        class DummyClient:
            def create_thread(self, comment_thread, project, repository_id, pull_request_id):
                calls.append({
                    "comment_thread": comment_thread,
                    "project": project,
                    "repository_id": repository_id,
                    "pull_request_id": pull_request_id,
                })
                return comment_thread

        # Build a minimal provider-like object (bypass __init__)
        provider = type("P", (), {})()
        provider.azure_devops_client = DummyClient()
        provider.workspace_slug = "my_workspace"
        provider.repo_slug = "my_repo"
        provider.pr_num = 42

        # One valid code suggestion (start present and end >= start)
        code_suggestions = [
            {
                "body": "Please consider refactoring this function.",
                "relevant_file": "/src/app.py",
                "relevant_lines_start": 10,
                "relevant_lines_end": 12,
            }
        ]

        # Call the unbound method with our dummy provider instance
        result = AzureDevopsProvider.publish_code_suggestions(provider, code_suggestions)

        # Assertions
        self.assertTrue(result)
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["project"], "my_workspace")
        self.assertEqual(call["repository_id"], "my_repo")
        self.assertEqual(call["pull_request_id"], 42)

        # Verify the comment content inside the constructed thread object
        thread_obj = call["comment_thread"]
        self.assertTrue(hasattr(thread_obj, "comments"))
        self.assertGreaterEqual(len(thread_obj.comments), 1)
        self.assertEqual(thread_obj.comments[0].content, "Please consider refactoring this function.")
