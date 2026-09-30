import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.custom_merge_loader')
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
        """Ensure loader aborts and logs an error when settings object has includes=True."""
        # Minimal dummy settings object that satisfies early checks in load()
        class DummySettings:
            def __init__(self):
                # non-empty list so loader proceeds past the settings_files check
                self.settings_files = ["ignored.toml"]
                # Trigger the forbidden-includes branch
                self.includes = True

        settings = DummySettings()

        # Patch the get_logger used by the loader so we can assert the error log call
        with patch("pr_agent.custom_merge_loader.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Import and invoke the loader under test
            from pr_agent.custom_merge_loader import load

            # Should return None (silent default True) and log an error
            result = load(settings)
            self.assertIsNone(result)

            mock_logger.error.assert_called_with(
                "Configuration includes forbidden option: 'includes'. Skipping loading."
            )
