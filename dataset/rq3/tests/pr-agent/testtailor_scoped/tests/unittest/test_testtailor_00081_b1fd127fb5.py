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
        """Unknown git_provider in settings raises the expected ValueError."""
        import types
        from unittest.mock import patch
        import pr_agent.git_providers as gp

        fake_settings = types.SimpleNamespace(
            config=types.SimpleNamespace(git_provider="not_a_provider")
        )

        # Patch the get_settings symbol that get_git_provider will call inside its module.
        with patch.object(gp, "get_settings", return_value=fake_settings):
            with self.assertRaisesRegex(ValueError, r"Unknown git provider: not_a_provider"):
                gp.get_git_provider()
