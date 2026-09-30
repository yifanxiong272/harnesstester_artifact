import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_provider')
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
        """Ensure __init__ handles exception from context.get and falls back to settings for bearer token
        while avoiding later AttributeError by providing a minimal PR object via a dummy Cloud client.
        """
        init_globals = BitbucketProvider.__init__.__globals__

        # Save originals
        orig_context = init_globals.get("context", None)
        orig_get_settings = init_globals.get("get_settings", None)
        orig_Cloud = init_globals.get("Cloud", None)

        # Context that raises on get
        class BadContext:
            def __init__(self):
                self.was_called = False

            def get(self, *args, **kwargs):
                self.was_called = True
                raise RuntimeError("simulated context failure")

        bad_context = BadContext()

        # Fake settings object used by get_settings()
        class FakeSettings:
            def __init__(self, mapping):
                self._mapping = mapping

            def get(self, key, default=None):
                return self._mapping.get(key, default)

        def fake_get_settings():
            return FakeSettings({
                "BITBUCKET.AUTH_TYPE": "bearer",
                "BITBUCKET.BEARER_TOKEN": "FAKE_TOKEN"
            })

        # Minimal Dummy Cloud + nested structure to return a PR with required __data links
        class DummyPR:
            def __init__(self):
                # Provide the minimal data used in __init__
                self._BitbucketBase__data = {
                    "links": {
                        "comments": {"href": "https://api.bitbucket.org/2.0/comments/1"},
                        "self": {"href": "https://api.bitbucket.org/2.0/pullrequests/1"}
                    }
                }

        class DummyPullRequests:
            def get(self, pr_num):
                return DummyPR()

        class DummyRepo:
            def __init__(self):
                self.pullrequests = DummyPullRequests()

        class DummyRepositories:
            def get(self, repo_slug):
                return DummyRepo()

        class DummyWorkspace:
            def __init__(self):
                self.repositories = DummyRepositories()

        class DummyWorkspaces:
            def get(self, workspace_slug):
                return DummyWorkspace()

        class DummyCloud:
            def __init__(self, session=None):
                self.session = session
                self.workspaces = DummyWorkspaces()

        try:
            # Patch globals
            init_globals["context"] = bad_context
            init_globals["get_settings"] = fake_get_settings
            init_globals["Cloud"] = DummyCloud

            # Provide a valid PR URL so __init__ sets self.pr and subsequent attributes
            pr_url = "https://bitbucket.org/WORKSPACE/REPO/pull-requests/123"

            provider = BitbucketProvider(pr_url=pr_url, incremental=False)

            # Verify context.get was attempted and we fell back to the settings-provided token
            assert getattr(bad_context, "was_called", False) is True
            assert hasattr(provider, "bearer_token")
            assert provider.bearer_token == "FAKE_TOKEN"
            # Also verify that bitbucket_comment_api_url was set from the dummy PR
            assert provider.bitbucket_comment_api_url == "https://api.bitbucket.org/2.0/comments/1"
        finally:
            # Restore originals
            if orig_context is not None:
                init_globals["context"] = orig_context
            else:
                init_globals.pop("context", None)
            if orig_get_settings is not None:
                init_globals["get_settings"] = orig_get_settings
            else:
                init_globals.pop("get_settings", None)
            if orig_Cloud is not None:
                init_globals["Cloud"] = orig_Cloud
            else:
                init_globals.pop("Cloud", None)
