import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.bitbucket_server_webhook')
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
        """Should ignore PRs when repository matches CONFIG.IGNORE_REPOSITORIES regex"""
        # Local imports to avoid relying on module-level imports in the test file
        import importlib
        from pr_agent.config_loader import get_settings

        bitbucket_server_webhook = importlib.import_module("pr_agent.servers.bitbucket_server_webhook")
        settings = get_settings()
        original_ignore_repos = settings.get("CONFIG.IGNORE_REPOSITORIES", [])

        # Prepare a Bitbucket Server style payload with project key PROJ and repo slug repo
        payload = {
            "pullRequest": {
                "id": 7,
                "title": "Regular PR",
                "fromRef": {"displayId": "feature/cache"},
                "toRef": {
                    "displayId": "main",
                    "repository": {
                        "slug": "repo",
                        "project": {"key": "PROJ"},
                    },
                },
                "author": {"user": {"name": "alice"}},
            }
        }

        # Set ignore repositories to match "PROJ/repo"
        settings.set("CONFIG.IGNORE_REPOSITORIES", ["PROJ/repo"])
        try:
            # The function should return False because the repo_full_name "PROJ/repo" matches the regex
            self.assertFalse(bitbucket_server_webhook.should_process_pr_logic(payload))
        finally:
            # Restore original setting
            settings.set("CONFIG.IGNORE_REPOSITORIES", original_ignore_repos)
