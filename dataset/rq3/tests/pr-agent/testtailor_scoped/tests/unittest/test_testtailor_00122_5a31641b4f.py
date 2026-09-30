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
        """When a GitProvider instance is already stored in the module-local context under the
        literal 'pr_url' key, get_git_provider_with_context should return that object (early-return path).

        To avoid interacting with the starlette_context ContextVar (which raises outside a request),
        replace the function's module-level `context` name with a plain dict for the duration of the test.
        """
        pr_url = "https://example.com/pr/42"
        sentinel_provider = object()

        # Patch the module-level `context` where the function is defined.
        import importlib
        func = get_git_provider_with_context
        mod = importlib.import_module(func.__module__)
        orig_context = getattr(mod, "context", None)

        try:
            # Use the literal key "pr_url" because the implementation checks context["git_provider"]["pr_url"]
            fake_context = {"settings": {"present": True}, "git_provider": {"pr_url": sentinel_provider}}
            setattr(mod, "context", fake_context)

            # Act
            result = get_git_provider_with_context(pr_url)

            # Assert: early-returned object should be exactly the sentinel we put into the context.
            self.assertIs(result, sentinel_provider)
        finally:
            # Restore original module context (best-effort).
            try:
                if orig_context is not None:
                    setattr(mod, "context", orig_context)
                else:
                    try:
                        delattr(mod, "context")
                    except Exception:
                        pass
            except Exception:
                pass
