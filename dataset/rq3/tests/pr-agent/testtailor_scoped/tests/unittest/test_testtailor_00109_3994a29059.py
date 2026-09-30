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
        """Ensure that when publish_output is enabled we publish the initial temporary comment."""
        # Prepare a fake settings object with required attributes
        class Cfg:
            def __init__(self):
                self.publish_output = True
                self.enable_custom_labels = False
                self.temperature = 0.0

            def get(self, k, default=None):
                return getattr(self, k, default)

        class Prompts:
            system = "system prompt"
            user = "user prompt"

        settings = type("S", (), {})()
        settings.config = Cfg()
        settings.pr_description = type("PD", (), {"extra_instructions": ""})()
        settings.pr_custom_labels_prompt = Prompts()
        settings.custom_labels = []

        # Dummy git provider to capture publish_comment calls
        class DummyProvider:
            def __init__(self, pr_url):
                self.pr = type("P", (), {"title": "PR Title"})()
                self._comments = []
                self.published_labels = None
                self.removed_initial = False

            def get_languages(self):
                return {}

            def get_files(self):
                return []

            def get_pr_id(self):
                return 42

            def get_pr_branch(self):
                return "branch"

            def get_pr_description(self, full=False):
                return "description"

            def get_commit_messages(self):
                return "commit1\ncommit2"

            def get_pr_labels(self):
                return ["user_label"]

            def is_supported(self, name):
                return False

            def publish_comment(self, text, is_temporary=False):
                # record the comment for assertions
                self._comments.append((text, is_temporary))

            def publish_labels(self, labels):
                self.published_labels = labels

            def remove_initial_comment(self):
                self.removed_initial = True

            @property
            def comments(self):
                return self._comments

        # Dummy AI handler (not used because we override _prepare_prediction)
        class DummyAIHandler:
            def __init__(self):
                self.main_pr_language = None

            async def chat_completion(self, *args, **kwargs):
                return "labels: ai_label", "stop"

        # Prepare to monkeypatch names used inside PRGenerateLabels' module
        import sys
        module = sys.modules[PRGenerateLabels.__module__]

        # Inject functions/objects into the module so PRGenerateLabels uses our fakes
        setattr(module, "get_settings", lambda use_context=False: settings)
        setattr(module, "get_git_provider", lambda: (lambda pr_url: DummyProvider(pr_url)))

        async def fake_retry_with_fallback_models(f, model_type=None):
            await f("dummy-model")

        setattr(module, "retry_with_fallback_models", fake_retry_with_fallback_models)

        # Instantiate the class under test
        obj = PRGenerateLabels("http://example.com/pr/1", ai_handler=DummyAIHandler)

        # Override the _prepare_prediction to avoid real diff/prediction logic
        async def fake_prepare(model):
            # set a minimal valid YAML prediction so _prepare_data/_prepare_labels succeed
            obj.prediction = "labels: auto_label"
            return None

        obj._prepare_prediction = fake_prepare

        # Run the method under test
        import asyncio
        asyncio.get_event_loop().run_until_complete(obj.run())

        # Assert that the initial publishing comment was created with is_temporary=True
        self.assertIn(("Preparing PR labels...", True), obj.git_provider.comments)
