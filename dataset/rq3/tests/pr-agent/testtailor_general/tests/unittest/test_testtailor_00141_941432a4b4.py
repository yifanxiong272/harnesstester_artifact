import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_code_suggestions')
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
        """When the git provider has no files, run() should log and return None."""
        # Create a PRCodeSuggestions instance without calling __init__
        pr = PRCodeSuggestions.__new__(PRCodeSuggestions)

        # Prepare a git_provider mock that returns falsy for get_files()
        git_provider_mock = unittest.mock.Mock()
        git_provider_mock.get_files.return_value = []  # no files -> falsy
        pr.git_provider = git_provider_mock
        pr.pr_url = "http://example.com/pr/1"
        pr.progress_response = None

        # Patch the get_logger function in the module where PRCodeSuggestions is defined
        module = __import__(PRCodeSuggestions.__module__, fromlist=['*'])
        mock_logger = unittest.mock.Mock()
        old_get_logger = getattr(module, "get_logger", None)
        try:
            # Replace get_logger with a lambda that returns our mock logger
            setattr(module, "get_logger", lambda *a, **k: mock_logger)

            # Run the async method
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(pr.run())

            # Assertions
            self.assertIsNone(result)
            mock_logger.info.assert_any_call(f"PR has no files: {pr.pr_url}, skipping code suggestions")
        finally:
            # Restore original get_logger to avoid side-effects
            if old_get_logger is not None:
                setattr(module, "get_logger", old_get_logger)
            else:
                delattr(module, "get_logger")
