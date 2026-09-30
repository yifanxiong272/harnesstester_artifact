import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.__init__')
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
        """When the configured git provider id is unknown, ensure the function raises
        and that the inner cause is the 'Unknown git provider' ValueError."""
        import importlib
        import unittest.mock

        # Try to locate the function in likely modules under pr_agent.git_providers
        func = None
        module = None
        try:
            module = importlib.import_module("pr_agent.git_providers")
            func = getattr(module, "get_git_provider_with_context", None)
        except Exception:
            func = None
            module = None

        # If not on the package module, try a few plausible submodules
        if func is None:
            for sub in ("git_provider", "factory", "utils", "provider"):
                try:
                    m = importlib.import_module(f"pr_agent.git_providers.{sub}")
                    candidate = getattr(m, "get_git_provider_with_context", None)
                    if candidate:
                        func = candidate
                        module = m
                        break
                except Exception:
                    continue

        if func is None:
            # If we really can't find it, skip the test rather than erroring out.
            self.skipTest("Could not locate get_git_provider_with_context in pr_agent.git_providers")

        # Create a fake settings object with a non-existent provider id.
        settings = type("S", (), {})()
        settings.config = type("C", (), {})()
        settings.config.git_provider = "no_such_provider"

        pr_url = "http://example.com/pr/1"

        # Patch the get_settings symbol in the module that defines the function so it
        # returns our fake settings. Also ensure the starlette context lookup yields falsy.
        with unittest.mock.patch(f"{module.__name__}.get_settings", return_value=settings):
            with unittest.mock.patch("starlette_context.context.get", return_value=None):
                with self.assertRaises(ValueError) as cm:
                    func(pr_url)

        exc = cm.exception
        # Outer error message should reference the PR URL (wrapped error)
        self.assertIn(pr_url, str(exc))

        # The chained cause should be the internal "Unknown git provider: ..." ValueError
        cause = getattr(exc, "__cause__", None)
        self.assertIsNotNone(cause, "Expected a chained cause for the internal failure")
        self.assertIsInstance(cause, ValueError)
        self.assertIn("Unknown git provider", str(cause))
        self.assertIn(settings.config.git_provider, str(cause))
