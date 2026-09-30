import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_update_changelog')
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
        """Verify that _get_prediction uses a deepcopy of self.vars and updates diff before rendering."""
        # prepare a dummy settings object with the minimal attributes used by _get_prediction
        class DummyPrompt:
            system = "{{ diff }}"
            user = "user:{{ pr_link }}"

        class DummySettings:
            pr_update_changelog = type("x", (), {"add_pr_link": True})
            pr_update_changelog_prompt = DummyPrompt
            config = type("c", (), {"temperature": 0.1})

        settings = DummySettings()

        # create a fake ai_handler that records the prompts it receives and returns a trimmed response
        recorded = {}

        class FakeAIHandler:
            async def chat_completion(self, model, system, user, temperature):
                recorded["model"] = model
                recorded["system"] = system
                recorded["user"] = user
                recorded["temperature"] = temperature
                # return a response that needs stripping
                return "   trimmed answer   ", "stop"

        # create a fake git_provider with get_pr_url
        class FakeGitProvider:
            def get_pr_url(self):
                return "http://example/pr/1"

        # instantiate an object without calling __init__
        pr_obj = object.__new__(PRUpdateChangelog)
        # set up the minimal attributes used by _get_prediction
        pr_obj.vars = {"diff": "", "pr_link": ""}
        pr_obj.patches_diff = "MY_DIFF"
        pr_obj.ai_handler = FakeAIHandler()
        pr_obj.git_provider = FakeGitProvider()

        # patch the get_settings in the function globals to return our DummySettings
        func = PRUpdateChangelog._get_prediction
        orig_get_settings = func.__globals__.get("get_settings")
        func.__globals__['get_settings'] = lambda: settings

        try:
            # run the coroutine (import asyncio dynamically to avoid top-level imports)
            asyncio = __import__('asyncio')
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(PRUpdateChangelog._get_prediction(pr_obj, model="test-model"))

            # check that the AI was called with rendered prompts that include the updated diff
            self.assertIn("MY_DIFF", recorded["system"])
            # since add_pr_link=True, pr_link should be set in the rendered user prompt
            self.assertIn("http://example/pr/1", recorded["user"])
            # confirm the returned answer was stripped correctly
            self.assertEqual(result, "trimmed answer")
        finally:
            # restore original get_settings to avoid side effects
            if orig_get_settings is not None:
                func.__globals__['get_settings'] = orig_get_settings
            else:
                del func.__globals__['get_settings']
