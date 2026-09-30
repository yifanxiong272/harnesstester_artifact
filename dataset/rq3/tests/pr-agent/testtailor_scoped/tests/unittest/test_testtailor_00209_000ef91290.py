import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_description')
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
        """Ensure semantic file types are disabled when provider doesn't support gfm_markdown."""
        # Local imports to avoid relying on module-level imports in the test file
        from pr_agent.config_loader import get_settings
        from pr_agent.git_providers import _GIT_PROVIDERS

        settings = get_settings()

        # Backup original semantic setting to restore later
        try:
            orig_semantic = settings.pr_description.enable_semantic_files_types
        except Exception:
            orig_semantic = None

        # Ensure the flag is initially True to trigger the branch in PRDescription.__init__
        try:
            settings.pr_description.enable_semantic_files_types = True
        except Exception:
            # best-effort set via settings.set if direct assign not supported
            try:
                settings.set("PR_DESCRIPTION.ENABLE_SEMANTIC_FILES_TYPES", True)
            except Exception:
                pass

        # Prepare a fake git provider class that explicitly does NOT support gfm_markdown
        class FakeProvider:
            def __init__(self, pr_url):
                from types import SimpleNamespace
                # minimal PR object with title used by PRDescription.vars
                self.pr = SimpleNamespace(title="fake PR", diff_files=[])
                self._pr_url = pr_url

            def get_languages(self):
                return {"Python": 100}

            def get_files(self):
                return ["file.py"]

            def get_pr_id(self):
                return "fake-pr-1"

            def is_supported(self, feature: str):
                # specifically return False for gfm_markdown to trigger the branch
                if feature == "gfm_markdown":
                    return False
                return False

            def get_pr_branch(self):
                return "branch"

            def get_pr_description(self, full=False):
                return "short description"

            def get_commit_messages(self):
                return "commit1"

            def get_diff_files(self):
                return []  # no diff files needed for this test

            def get_user_description(self):
                return "user provided description"

            def get_pr_url(self):
                return self._pr_url

            def get_pr_labels(self, update=False):
                return []

        provider_key = "unit_test_fake_provider"
        original_provider = _GIT_PROVIDERS.get(provider_key, None)
        try:
            # Register our fake provider and point settings to use it
            _GIT_PROVIDERS[provider_key] = FakeProvider
            settings.set("CONFIG.GIT_PROVIDER", provider_key)

            # Dummy AI handler class — PRDescription will instantiate it but we don't need to call it
            class DummyAIHandler:
                def __init__(self):
                    pass

                async def chat_completion(self, model, system, user, temperature=0.2, **kwargs):
                    return "", "stop"

            # Act: instantiate PRDescription which should detect unsupported gfm_markdown and
            # therefore set the enable_semantic_files_types flag to False
            pr_desc = PRDescription("any-pr-url", ai_handler=DummyAIHandler)

            # Assert: the setting has been toggled off by __init__
            self.assertFalse(
                get_settings().pr_description.enable_semantic_files_types,
                "Expected enable_semantic_files_types to be set to False when gfm_markdown is not supported"
            )
        finally:
            # Restore original provider mapping
            if original_provider is not None:
                _GIT_PROVIDERS[provider_key] = original_provider
            else:
                _GIT_PROVIDERS.pop(provider_key, None)

            # Restore original semantic setting
            try:
                if orig_semantic is None:
                    # best-effort unset or set safe default
                    try:
                        settings.pr_description.unset("enable_semantic_files_types")
                    except Exception:
                        settings.pr_description.enable_semantic_files_types = False
                else:
                    settings.pr_description.enable_semantic_files_types = orig_semantic
            except Exception:
                # last resort: attempt via settings.set
                try:
                    settings.set("PR_DESCRIPTION.ENABLE_SEMANTIC_FILES_TYPES", bool(orig_semantic))
                except Exception:
                    pass
