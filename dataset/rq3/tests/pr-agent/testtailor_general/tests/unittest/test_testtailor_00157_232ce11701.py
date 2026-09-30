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
        """Ensure CONFIG.IGNORE_PR_TITLE handles a non-list (string) value by being coerced to a list."""
        import importlib
        from pr_agent.config_loader import get_settings

        bitbucket_server_webhook = importlib.import_module("pr_agent.servers.bitbucket_server_webhook")

        settings = get_settings()
        original = settings.get("CONFIG.IGNORE_PR_TITLE", [])
        # Set the setting to a string (not a list) to hit the branch where it's converted to a list
        settings.set("CONFIG.IGNORE_PR_TITLE", "^WIP")
        try:
            payload = {
                "pullRequest": {
                    "id": 1,
                    "title": "WIP: work in progress",
                    "fromRef": {"displayId": "feature/x"},
                    "toRef": {
                        "displayId": "main",
                        "repository": {"slug": "repo", "project": {"key": "PROJ"}},
                    },
                    "author": {"user": {"name": "alice"}},
                }
            }
            # The title matches the regex string set above; should_process_pr_logic should return False
            self.assertFalse(bitbucket_server_webhook.should_process_pr_logic(payload))
        finally:
            # restore original setting
            settings.set("CONFIG.IGNORE_PR_TITLE", original)
