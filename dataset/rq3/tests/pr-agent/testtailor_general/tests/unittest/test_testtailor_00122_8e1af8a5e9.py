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
        """When the configured git_provider is not in _GIT_PROVIDERS, get_git_provider()
        should raise a ValueError with an appropriate message.

        This test searches the pr_agent package for the module that defines get_git_provider,
        patches that module's get_settings to return a fake settings object with an unknown
        provider id, and asserts that calling get_git_provider raises the expected ValueError.
        """
        import types
        import pkgutil
        import importlib
        from unittest.mock import patch
        import pr_agent

        # Build a fake settings object whose config.git_provider is unknown
        fake_settings = types.SimpleNamespace(config=types.SimpleNamespace(git_provider="not-a-real"))

        # Locate the module that defines get_git_provider inside the pr_agent package
        get_git_provider = None
        provider_module = None
        for finder, name, ispkg in pkgutil.walk_packages(pr_agent.__path__, prefix=pr_agent.__name__ + "."):
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            if hasattr(mod, "get_git_provider"):
                candidate = getattr(mod, "get_git_provider")
                if callable(candidate):
                    get_git_provider = candidate
                    provider_module = mod
                    break

        self.assertIsNotNone(get_git_provider, "get_git_provider not found in any pr_agent submodule")

        # Patch the get_settings name where get_git_provider will look it up (module-local),
        # so the function sees our fake settings.
        with patch.object(provider_module, "get_settings", return_value=fake_settings):
            with self.assertRaises(ValueError) as cm:
                get_git_provider()

        self.assertIn("Unknown git provider: not-a-real", str(cm.exception))
