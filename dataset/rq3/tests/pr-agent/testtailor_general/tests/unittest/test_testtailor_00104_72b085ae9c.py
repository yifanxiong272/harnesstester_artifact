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
        """Ensure run() reaches the initial logger info line without performing AI work or publishing."""
        # Backup originals from the module where PRGenerateLabels is defined
        mod = __import__('pr_agent.tools.pr_generate_labels', fromlist=['pr_generate_labels'])
        orig_get_git_provider = getattr(mod, 'get_git_provider', None)
        orig_retry = getattr(mod, 'retry_with_fallback_models', None)
        orig_TokenHandler = getattr(mod, 'TokenHandler', None)

        try:
            # Ensure publish_output is disabled to avoid calling git provider publish methods
            settings = get_settings()
            try:
                settings.config.publish_output = False
            except Exception:
                # best effort, some settings objects may behave differently
                pass

            # Fake provider to avoid network / git interactions
            class FakePR:
                def __init__(self):
                    self.title = "fake title"

            class FakeProvider:
                def __init__(self, pr_url):
                    self.pr = FakePR()

                def get_languages(self):
                    return []

                def get_files(self):
                    return []

                def get_pr_id(self):
                    return "42"

                def get_pr_branch(self):
                    return "branch"

                def get_pr_description(self, full=False):
                    return "desc"

                def get_commit_messages(self):
                    return ""

                def publish_comment(self, text, is_temporary=False):
                    # record but do nothing
                    self._last_comment = (text, is_temporary)

                def get_pr_labels(self):
                    return []

                def is_supported(self, name):
                    return False

                def publish_labels(self, labels):
                    self._published_labels = labels

                def remove_initial_comment(self):
                    self._removed = True

            # Patch get_git_provider to return our FakeProvider constructor
            def fake_get_git_provider():
                return FakeProvider

            # Patch retry_with_fallback_models so it doesn't call the heavy AI path
            async def fake_retry(func):
                # Simulate a successful attempt but do not invoke func to keep prediction None
                return None

            # Replace TokenHandler with a lightweight fake to avoid settings dependencies
            class FakeTokenHandler:
                def __init__(self, pr, vars, system, user):
                    self.pr = pr
                    self.vars = vars

            # Simple fake AI handler to avoid instantiating real handlers
            class FakeAIHandler:
                def __init__(self):
                    self.main_pr_language = None

                async def chat_completion(self, model, temperature, system, user):
                    return ("", None)

            # Apply patches in the module scope
            mod.get_git_provider = fake_get_git_provider
            mod.retry_with_fallback_models = fake_retry
            mod.TokenHandler = FakeTokenHandler

            # Instantiate PRGenerateLabels with the fake AI handler to avoid side-effects
            pr = mod.PRGenerateLabels("http://fake-pr", ai_handler=FakeAIHandler)

            # Run the async run() method in a fresh event loop
            loop = __import__('asyncio').new_event_loop()
            try:
                __import__('asyncio').set_event_loop(loop)
                result = loop.run_until_complete(pr.run())
            finally:
                loop.close()

            # Because fake_retry does not set pr.prediction, the method returns None inside the try
            self.assertIsNone(result)
        finally:
            # Restore originals
            if orig_get_git_provider is not None:
                mod.get_git_provider = orig_get_git_provider
            if orig_retry is not None:
                mod.retry_with_fallback_models = orig_retry
            if orig_TokenHandler is not None:
                mod.TokenHandler = orig_TokenHandler
