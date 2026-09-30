import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_generate_labels')
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
        """Test PRGenerateLabels __init__ sets up git provider, AI handler, vars and token handler."""
        # Fake AI handler to pass into PRGenerateLabels
        class FakeAIHandler:
            def __init__(self):
                # will be set by PRGenerateLabels after construction
                self.main_pr_language = None

        # Fake TokenHandler to capture constructor arguments
        class FakeTokenHandler:
            def __init__(self, pr, vars, system, user):
                self.pr = pr
                self.vars = vars
                self.system = system
                self.user = user
                # emulate prompt_tokens attribute used elsewhere
                self.prompt_tokens = 0

        # Prepare fakes for git provider and settings
        provider_instance = MagicMock()
        class PRObj:
            pass
        pr_obj = PRObj()
        pr_obj.title = "Test PR Title"
        provider_instance.pr = pr_obj
        provider_instance.get_languages.return_value = {"Python": 100}
        provider_instance.get_files.return_value = ["file.py"]
        provider_instance.get_pr_id.return_value = "pr-123"
        provider_instance.get_pr_branch.return_value = "feature/awesome"
        # ensure signature matches call get_pr_description(full=False)
        provider_instance.get_pr_description.side_effect = lambda full=False: "Short description"
        provider_instance.get_commit_messages.return_value = "commit1\ncommit2"

        # Create a fake settings object with needed nested attributes
        class FakeSettings:
            pass
        fake_settings = FakeSettings()
        fake_settings.pr_description = type("X", (), {"extra_instructions": "Be concise"})
        fake_settings.config = type("Y", (), {"enable_custom_labels": True})
        fake_settings.pr_custom_labels_prompt = type("Z", (), {"system": "SYSTEM_PROMPT", "user": "USER_PROMPT"})

        # Monkeypatch the globals used by PRGenerateLabels.__init__ directly to avoid import path issues
        init_globals = PRGenerateLabels.__init__.__globals__
        save = {
            "get_git_provider": init_globals.get("get_git_provider"),
            "get_main_pr_language": init_globals.get("get_main_pr_language"),
            "get_settings": init_globals.get("get_settings"),
            "TokenHandler": init_globals.get("TokenHandler"),
        }

        try:
            # get_git_provider() should return a callable that when called with pr_url returns provider_instance
            init_globals["get_git_provider"] = (lambda: (lambda pr_url: provider_instance))
            init_globals["get_main_pr_language"] = (lambda languages, files: "python")
            init_globals["get_settings"] = (lambda use_context=False: fake_settings)
            init_globals["TokenHandler"] = FakeTokenHandler

            # Instantiate the target object, injecting FakeAIHandler
            agent = PRGenerateLabels("https://example.com/pr/1", ai_handler=FakeAIHandler)

            # Verify git provider was set properly
            self.assertIs(agent.git_provider, provider_instance)
            self.assertEqual(agent.pr_id, "pr-123")

            # Verify main_pr_language propagated to ai_handler
            self.assertEqual(agent.main_pr_language, "python")
            self.assertIsInstance(agent.ai_handler, FakeAIHandler)
            self.assertEqual(agent.ai_handler.main_pr_language, "python")

            # Verify vars content
            self.assertIn("title", agent.vars)
            self.assertEqual(agent.vars["title"], "Test PR Title")
            self.assertEqual(agent.vars["branch"], "feature/awesome")
            self.assertEqual(agent.vars["description"], "Short description")
            self.assertEqual(agent.vars["language"], "python")
            self.assertEqual(agent.vars["diff"], "")
            self.assertEqual(agent.vars["extra_instructions"], "Be concise")
            self.assertEqual(agent.vars["commit_messages_str"], "commit1\ncommit2")
            self.assertTrue(agent.vars["enable_custom_labels"])
            self.assertEqual(agent.vars["custom_labels_class"], "")

            # Verify TokenHandler was called and attached
            self.assertIsInstance(agent.token_handler, FakeTokenHandler)
            # token handler should have been initialized with the PR object and the same vars dict
            self.assertIs(agent.token_handler.pr, provider_instance.pr)
            self.assertIs(agent.token_handler.vars, agent.vars)
            self.assertEqual(agent.token_handler.system, "SYSTEM_PROMPT")
            self.assertEqual(agent.token_handler.user, "USER_PROMPT")

            # Verify patches_diff and prediction initialized to None
            self.assertIsNone(agent.patches_diff)
            self.assertIsNone(agent.prediction)
        finally:
            # restore original globals to avoid side effects for other tests
            for k, v in save.items():
                if v is None:
                    init_globals.pop(k, None)
                else:
                    init_globals[k] = v
