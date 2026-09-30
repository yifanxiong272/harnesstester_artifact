import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.github.service.repos')
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
        """Test that get_installations returns string IDs for installations."""
        # Create a concrete subclass to satisfy abstract methods
        class DummyGitHubReposMixin(GitHubReposMixin):
            def _get_cursorrules_url(self, *args, **kwargs):
                return ""
            def _get_file_name_from_item(self, *args, **kwargs):
                return ""
            def _get_file_path_from_item(self, *args, **kwargs):
                return ""
            def _get_microagents_directory_params(self, *args, **kwargs):
                return {}
            def _get_microagents_directory_url(self, *args, **kwargs):
                return ""
            def _is_valid_microagent_file(self, *args, **kwargs):
                return False

        mixin = DummyGitHubReposMixin()
        mixin.BASE_URL = 'https://api.github.com'

        async def fake_make_request(url, *args, **kwargs):
            # Simulate GitHub response with numeric and string IDs
            return ({"installations": [{"id": 123}, {"id": "456"}]}, {})

        # Attach the fake request function to the instance
        mixin._make_request = fake_make_request

        # Import asyncio at runtime to avoid top-level import statements
        asyncio = __import__('asyncio')

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(mixin.get_installations())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        self.assertEqual(result, ["123", "456"])
